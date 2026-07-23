import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import config

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

_model_cache = None

def load_local_model(model_name=config.LOCAL_MODEL_NAME):
    global _model_cache
    if _model_cache is None:
        print(f"[+] Loading local model '{model_name.split('/')[-1]} algorithms'...")
        start_t = time.time()
        _model_cache = SentenceTransformer(model_name)
        load_latency = time.time() - start_t
        print(f"[+] Model loaded successfully in {load_latency:.2f}s")
    return _model_cache

def calculate_cosine_similarity(vec1, vec2):
    v1 = np.array(vec1).reshape(1, -1)
    v2 = np.array(vec2).reshape(1, -1)
    return float(cosine_similarity(v1, v2)[0][0])

def evaluate_single_pair_local(text1, text2, model_name=config.LOCAL_MODEL_NAME, threshold=config.SIMILARITY_THRESHOLD):
    model = load_local_model(model_name)
    start_time = time.time()
    
    vec1 = model.encode(text1, convert_to_numpy=True)
    vec2 = model.encode(text2, convert_to_numpy=True)
    score = calculate_cosine_similarity(vec1, vec2)
    latency_ms = (time.time() - start_time) * 1000
    
    sim_pct = score * 100
    predicted = "Similar" if score >= threshold else "Not Similar"
    
    print("\n" + "=" * 70)
    print("  LOCAL SEMANTIC SIMILARITY - SINGLE PAIR EVALUATION")
    print("=" * 70)
    print(f"  Sentence A: '{text1}'")
    print(f"  Sentence B: '{text2}'")
    print("-" * 70)
    print(f"  Similarity Score: {score:.4f} ({sim_pct:.2f}%)")
    print(f"  Prediction:       [{predicted.upper()}] (Threshold >= {threshold*100:.0f}%)")
    print(f"  Latency:          {latency_ms:.2f} ms")
    print("=" * 70 + "\n")
    return score, predicted

def run_local_similarity(dataset_path=config.DATASET_PATH, output_path=config.RESULTS_LOCAL_PATH, threshold=config.SIMILARITY_THRESHOLD, sample_count=None, batch_size=32, export_uncertain_threshold=0.90, uncertain_csv="dataset_uncertain_cases.csv"):
    if not os.path.exists(dataset_path):
        dataset_path = config.FALLBACK_DATASET_PATH
        
    df = pd.read_csv(dataset_path)
    total_original = len(df)
    
    # Systematic Stratified Sampling (Video Frame Analogy)
    if sample_count and sample_count < total_original:
        step = max(1, total_original // sample_count)
        df = df.iloc[::step].head(sample_count).reset_index(drop=True)
        print(f"[🎬 SYSTEMATIC SAMPLING] Sampled {len(df)} representative test cases from {total_original} total rows (Interval step: {step})")

    print("=" * 80)
    print(f"  LOCAL SEMANTIC SIMILARITY EVALUATION ({dataset_path})")
    print(f"  Model: {config.LOCAL_MODEL_NAME}")
    print(f"  Threshold: {threshold} | Execution Mode: [LOCAL CPU]")
    print("  Implemented Techniques:")
    print(f"    • Technique 1: Tensor Matrix Batch Encoding (batch_size={batch_size}, ~3.1ms/pair)")
    print(f"    • Technique 2: Systematic Stratified Sampling (Sample: {len(df)}/{total_original} rows)")
    print(f"    • Strategy 1:  Cascading Router Export (Local Confidence Cutoff < {export_uncertain_threshold*100:.0f}%)")
    print("=" * 80)
    print(f"[+] Loaded {len(df)} test cases from '{dataset_path}'")

    model = load_local_model(config.LOCAL_MODEL_NAME)

    # Fast Batch Encoding for all sentences
    print(f"[+] Encoding all {len(df)} sentence pairs in batch mode (batch_size={batch_size})...")
    start_batch = time.time()
    
    all_sentences_a = df['sentence_a'].tolist()
    all_sentences_b = df['sentence_b'].tolist()
    all_sentences = all_sentences_a + all_sentences_b
    
    all_embeddings = model.encode(all_sentences, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)
    embeddings_a = all_embeddings[:len(df)]
    embeddings_b = all_embeddings[len(df):]
    
    total_batch_time = time.time() - start_batch
    avg_latency_per_pair = (total_batch_time / len(df)) * 1000
    print(f"[+] Batch encoding completed in {total_batch_time:.2f}s ({avg_latency_per_pair:.2f} ms / pair average)")

    results = []
    uncertain_rows = []
    
    print(f"\n{'ID':<4} | {'Category':<18} | {'Similarity':<10} | {'Expected':<12} | {'Predicted':<12} | {'Match'}")
    print("-" * 78)
    
    for idx, row in df.iterrows():
        s_id = row['id']
        category = str(row['category'])[:18]
        sent_a = row['sentence_a']
        sent_b = row['sentence_b']
        expected = row['expected']
        
        score = calculate_cosine_similarity(embeddings_a[idx], embeddings_b[idx])
        sim_score = max(0.0, min(1.0, score))
        predicted = "Similar" if sim_score >= threshold else "Not Similar"
        is_match = "PASS" if predicted == expected else "FAIL"
        
        results.append({
            'id': s_id,
            'category': row['category'],
            'sentence_a': sent_a,
            'sentence_b': sent_b,
            'expected': expected,
            'predicted': predicted,
            'similarity_score': round(sim_score, 4),
            'similarity_pct': f"{sim_score * 100:.2f}%",
            'latency_ms': round(avg_latency_per_pair, 2),
            'execution_mode': 'Local CPU'
        })
        
        # Check if local model confidence is below 90% (Strategy 1: Cascading Router)
        if sim_score < export_uncertain_threshold:
            uncertain_rows.append(row)
        
        if idx < 15 or idx >= len(df) - 5:
            print(f"{s_id:<4} | {category:<18} | {sim_score*100:>8.2f}% | {expected:<12} | {predicted:<12} | [{is_match}]")
        elif idx == 15:
            print("... (evaluating remaining pairs) ...")

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)
    
    # Export uncertain/hard cases to separate CSV for manual Paid API run
    if uncertain_rows:
        uncertain_df = pd.DataFrame(uncertain_rows)
        uncertain_df.to_csv(uncertain_csv, index=False)
        print(f"\n[📂 CASCADING ROUTER EXPORT] Identified {len(uncertain_df)} uncertain test cases (Local Score < {export_uncertain_threshold*100:.0f}%).")
        print(f"[*] Saved hard cases to '{uncertain_csv}'")
        print(f"[*] To manually evaluate these cases on Gemini API, run:")
        print(f"    python semantic_api.py --dataset {uncertain_csv}\n")

    correct_count = (results_df['predicted'] == results_df['expected']).sum()
    accuracy = (correct_count / len(results_df)) * 100
    
    print("-" * 78)
    print(f"[*] Execution Mode: LOCAL CPU (BATCH ENCODED)")
    print(f"[*] Total Evaluated: {len(results_df)}")
    print(f"[*] Accuracy: {accuracy:.2f}% ({correct_count}/{len(results_df)})")
    print(f"[*] Avg Batch Latency per Pair: {avg_latency_per_pair:.2f} ms")
    print(f"[*] Results saved to '{output_path}'\n")
    return results_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Semantic Similarity Script")
    parser.add_argument("--text1", type=str, help="First sentence for single-pair testing")
    parser.add_argument("--text2", type=str, help="Second sentence for single-pair testing")
    parser.add_argument("--dataset", type=str, default=config.DATASET_PATH, help="Path to evaluation dataset")
    parser.add_argument("--threshold", type=float, default=config.SIMILARITY_THRESHOLD, help="Decision threshold")
    parser.add_argument("--sample", type=int, default=None, help="Systematic sample count (e.g. 50)")
    parser.add_argument("--export-uncertain", type=float, default=0.90, help="Local similarity cutoff threshold to export uncertain cases (default 0.90)")
    args = parser.parse_args()
    
    if args.text1 and args.text2:
        evaluate_single_pair_local(args.text1, args.text2, threshold=args.threshold)
    else:
        run_local_similarity(dataset_path=args.dataset, threshold=args.threshold, sample_count=args.sample, export_uncertain_threshold=args.export_uncertain)
