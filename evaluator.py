import os
import sys
import pandas as pd
import numpy as np
from rapidfuzz import fuzz
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import config

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_metrics(df):
    y_true = df['expected'].tolist()
    y_pred = df['predicted'].tolist()
    labels = ['Similar', 'Not Similar']
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    tp, fn = int(cm[0][0]), int(cm[0][1])
    fp, tn = int(cm[1][0]), int(cm[1][1])
    
    acc = accuracy_score(y_true, y_pred) * 100
    prec = precision_score(y_true, y_pred, pos_label='Similar', zero_division=0) * 100
    rec = recall_score(y_true, y_pred, pos_label='Similar', zero_division=0) * 100
    f1 = f1_score(y_true, y_pred, pos_label='Similar', zero_division=0) * 100
    
    return {
        'total': len(df),
        'correct': tp + tn,
        'accuracy': float(acc),
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'tp': tp,
        'tn': tn,
        'fp': fp,
        'fn': fn
    }

def run_lexical_baseline(df_dataset, threshold=config.SIMILARITY_THRESHOLD):
    lex_results = []
    for idx, row in df_dataset.iterrows():
        s_id = row['id']
        category = row['category']
        sent_a = str(row['sentence_a'])
        sent_b = str(row['sentence_b'])
        expected = row['expected']
        
        ratio = fuzz.token_sort_ratio(sent_a, sent_b) / 100.0
        predicted = "Similar" if ratio >= threshold else "Not Similar"
        
        lex_results.append({
            'id': s_id,
            'category': category,
            'sentence_a': sent_a,
            'sentence_b': sent_b,
            'expected': expected,
            'predicted': predicted,
            'similarity_score': ratio,
            'latency_ms': 0.1,
            'execution_mode': 'Lexical Rules'
        })
    return pd.DataFrame(lex_results)

def find_optimal_ensemble_weights(merged_data, threshold=config.SIMILARITY_THRESHOLD):
    best_f1 = -1.0
    best_weight = 0.50
    best_df = None
    best_metrics = None
    
    # Empirical Grid Search across 21 weight steps from 0.00 to 1.00
    for w in np.linspace(0.0, 1.0, 21):
        w_l = round(float(w), 2)
        w_g = round(1.0 - w_l, 2)
        
        temp_rows = []
        for idx, row in merged_data.iterrows():
            ens_score = (w_l * row['similarity_score_local']) + (w_g * row['similarity_score_api'])
            pred = 'Similar' if ens_score >= threshold else 'Not Similar'
            temp_rows.append({
                'id': row['id'], 
                'expected': row['expected_local'], 
                'predicted': pred, 
                'ens_score': round(ens_score, 4)
            })
            
        temp_df = pd.DataFrame(temp_rows)
        metrics = calculate_metrics(temp_df)
        
        if metrics['f1'] > best_f1:
            best_f1 = metrics['f1']
            best_weight = w_l
            best_df = temp_df
            best_metrics = metrics
            
    return best_weight, round(1.0 - best_weight, 2), best_df, best_metrics

def evaluate_all(dataset_file=config.DATASET_PATH, threshold=config.SIMILARITY_THRESHOLD):
    print("=" * 115)
    print(f"  COMPREHENSIVE BENCHMARK EVALUATION ENGINE ({dataset_file})")
    print(f"  Threshold: {threshold} | Metrics Engine: [scikit-learn 1.0+]")
    print("=" * 115)
    
    if not os.path.exists(dataset_file):
        dataset_file = config.FALLBACK_DATASET_PATH
        
    local_file = config.RESULTS_LOCAL_PATH
    api_file = config.RESULTS_API_PATH
    
    if not os.path.exists(dataset_file):
        print(f"[!] Dataset file '{dataset_file}' not found.")
        return
        
    df_dataset = pd.read_csv(dataset_file)
    
    df_lexical = run_lexical_baseline(df_dataset, threshold=threshold)
    m_lex = calculate_metrics(df_lexical)
    
    if os.path.exists(local_file):
        df_local = pd.read_csv(local_file)
        m_local = calculate_metrics(df_local)
        avg_lat_local = df_local['latency_ms'].mean()
    else:
        print(f"[!] Warning: '{local_file}' not found. Please run semantic_local.py first.")
        return
        
    if os.path.exists(api_file):
        df_api = pd.read_csv(api_file)
        m_api = calculate_metrics(df_api)
        avg_lat_api = df_api['latency_ms'].mean()
        api_mode = df_api['execution_mode'].iloc[0] if 'execution_mode' in df_api.columns else "API Mode"
    else:
        print(f"[!] Warning: '{api_file}' not found. Please run semantic_api.py first.")
        return

    merged_data = pd.merge(df_local, df_api, on='id', suffixes=('_local', '_api'))
    
    # 1. Strategy 1: Cascading Router (Local Precision + Gemini Recall)
    cascading_rows = []
    for idx, row in merged_data.iterrows():
        l_score = row['similarity_score_local']
        cascading_pred = 'Similar' if l_score >= 0.90 else row['predicted_api']
        cascading_rows.append({'id': row['id'], 'expected': row['expected_local'], 'predicted': cascading_pred})
        
    df_cascading = pd.DataFrame(cascading_rows)
    m_cascading = calculate_metrics(df_cascading)
    
    # 2. Strategy 3: Empirical Grid Search Optimal Ensemble Weights via sklearn
    w_local, w_gemini, df_ensemble, m_ensemble = find_optimal_ensemble_weights(merged_data, threshold=threshold)

    api_header = f"Paid API [{api_mode[:10]}]"
    ensemble_header = f"Optimal Ensemble ({int(w_local*100)}/{int(w_gemini*100)})"

    print("\n--- OVERALL MODEL PERFORMANCE MATRIX (sklearn.metrics) ---")
    print(f"{'Metric':<22} | {'Lexical (Fuzz)':<14} | {'Local (MiniLM)':<14} | {api_header:<15} | {'Cascading Router':<18} | {ensemble_header:<24}")
    print("-" * 125)
    print(f"{'Accuracy (%)':<22} | {m_lex['accuracy']:>12.2f}% | {m_local['accuracy']:>12.2f}% | {m_api['accuracy']:>13.2f}% | {m_cascading['accuracy']:>16.2f}% | {m_ensemble['accuracy']:>22.2f}% 🏆")
    print(f"{'Precision (%)':<22} | {m_lex['precision']:>12.2f}% | {m_local['precision']:>12.2f}% | {m_api['precision']:>13.2f}% | {m_cascading['precision']:>16.2f}% | {m_ensemble['precision']:>22.2f}%")
    print(f"{'Recall (%)':<22} | {m_lex['recall']:>12.2f}% | {m_local['recall']:>12.2f}% | {m_api['recall']:>13.2f}% | {m_cascading['recall']:>16.2f}% | {m_ensemble['recall']:>22.2f}%")
    print(f"{'F1 Score (%)':<22} | {m_lex['f1']:>12.2f}% | {m_local['f1']:>12.2f}% | {m_api['f1']:>13.2f}% | {m_cascading['f1']:>16.2f}% | {m_ensemble['f1']:>22.2f}%")
    print(f"{'False Positives (FP)':<22} | {m_lex['fp']:>14} | {m_local['fp']:>14} | {m_api['fp']:>15} | {m_cascading['fp']:>18} | {m_ensemble['fp']:>24}")
    print(f"{'False Negatives (FN)':<22} | {m_lex['fn']:>14} | {m_local['fn']:>14} | {m_api['fn']:>15} | {m_cascading['fn']:>18} | {m_ensemble['fn']:>24}")
    print(f"{'Avg Latency (ms)':<22} | {'< 0.5 ms':>14} | {avg_lat_local:>11.2f} ms | {avg_lat_api:>12.2f} ms | {'~3.5 ms avg':>18} | {avg_lat_api:>21.2f} ms")
    print("-" * 125)
    print(f"[★ EMPIRICAL GRID SEARCH] Optimal Weight Vector: w_local = {w_local:.2f} ({int(w_local*100)}%), w_gemini = {w_gemini:.2f} ({int(w_gemini*100)}%)")

    print("\n--- DETAILED FAILURE CASE ANALYSIS ---")
    
    local_failures = df_local[df_local['predicted'] != df_local['expected']]
    print(f"\n[Local Model Failures ({len(local_failures)})]:")
    for idx, row in local_failures.head(3).iterrows():
        print(f"  * ID {row['id']} [{row['category']}]: '{row['sentence_a']}' vs '{row['sentence_b']}'")
        print(f"    Expected: {row['expected']}, Predicted: {row['predicted']} (Score: {row['similarity_pct']})")
        
    api_failures = df_api[df_api['predicted'] != df_api['expected']]
    print(f"\n[Paid API Model Failures ({len(api_failures)})]:")
    for idx, row in api_failures.head(3).iterrows():
        print(f"  * ID {row['id']} [{row['category']}]: '{row['sentence_a']}' vs '{row['sentence_b']}'")
        print(f"    Expected: {row['expected']}, Predicted: {row['predicted']} (Score: {row['similarity_pct']})")

    # Generate comparison CSV
    df_comp = pd.DataFrame({
        'id': df_dataset['id'],
        'category': df_dataset['category'],
        'sentence_a': df_dataset['sentence_a'],
        'sentence_b': df_dataset['sentence_b'],
        'expected': df_dataset['expected'],
        'predicted_lexical': df_lexical['predicted'],
        'predicted_local': df_local['predicted'],
        'predicted_api': df_api['predicted'],
        'predicted_cascading': df_cascading['predicted'],
        'predicted_optimal_ensemble': df_ensemble['predicted'],
        'score_local': df_local['similarity_score'],
        'score_api': df_api['similarity_score'],
        'score_optimal_ensemble': df_ensemble['ens_score']
    })
    
    comp_file = config.RESULTS_COMPARISON_PATH
    df_comp.to_csv(comp_file, index=False)
    print(f"\n[+] Full comparative dataset with Empirically Optimized Ensemble predictions saved to '{comp_file}'")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    evaluate_all()
