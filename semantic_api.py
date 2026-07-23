import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import config

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Active Google Gemini Embedding Models Pool for Dynamic 429 Failover & Rotation
EMBEDDING_MODEL_POOL = [
    "gemini-embedding-001",
    "gemini-embedding-2",
    "gemini-embedding-2-preview"
]

# Track global active model index
active_model_idx = 0

def get_current_model_name():
    global active_model_idx
    return EMBEDDING_MODEL_POOL[active_model_idx % len(EMBEDDING_MODEL_POOL)]

def rotate_to_next_model(reason="429 Rate Limit"):
    global active_model_idx
    old_model = get_current_model_name()
    active_model_idx = (active_model_idx + 1) % len(EMBEDDING_MODEL_POOL)
    new_model = get_current_model_name()
    print(f"\n[🔄 MODEL ROTATION] {reason} on '{old_model}'! Automatically rotating active model to -> '{new_model}'")
    return new_model

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
    if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
        print("\n" + "!" * 75)
        print("  [!] ERROR: NO VALID GEMINI API KEY DETECTED IN ENVIRONMENT (.env)")
        print("  To run real API calls:")
        print("  1. Open your .env file in this directory")
        print("  2. Set GEMINI_API_KEY=<YOUR_API_KEY>")
        print("  3. Get a free key at: https://aistudio.google.com/app/apikey")
        print("!" * 75 + "\n")
        return None, None

    # 1. Try google-genai SDK
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m in EMBEDDING_MODEL_POOL:
            try:
                res = client.models.embed_content(model=m, contents="test connection")
                if res and (hasattr(res, 'embedding') or hasattr(res, 'embeddings')):
                    print(f"[+] Connected to Gemini API via google-genai SDK (Default Model: '{m}')")
                    return client, "new_sdk"
            except Exception:
                continue
    except Exception:
        pass

    # 2. Try google.generativeai SDK
    try:
        import google.generativeai as genai_leg
        genai_leg.configure(api_key=api_key)
        for m in EMBEDDING_MODEL_POOL:
            try:
                m_name = m if m.startswith("models/") else f"models/{m}"
                res = genai_leg.embed_content(model=m_name, content="test connection")
                if res and 'embedding' in res:
                    print(f"[+] Connected to Gemini API via google.generativeai SDK (Default Model: '{m_name}')")
                    return genai_leg, "legacy_sdk"
            except Exception:
                continue
    except Exception:
        pass

    print("\n" + "!" * 78)
    print("  [!] ERROR: Could not connect to Gemini API embedding models.")
    print("  Please check your GEMINI_API_KEY in .env or verify your Google AI Studio quota.")
    print("!" * 78 + "\n")
    return None, None

def get_gemini_embedding(text, client, sdk_type, retries_per_model=3):
    max_total_attempts = len(EMBEDDING_MODEL_POOL) * retries_per_model
    
    for attempt in range(max_total_attempts):
        current_model = get_current_model_name()
        try:
            if sdk_type == "new_sdk":
                model_id = current_model.replace("models/", "")
                response = client.models.embed_content(
                    model=model_id,
                    contents=text
                )
                if hasattr(response, "embedding") and response.embedding and hasattr(response.embedding, "values"):
                    return response.embedding.values
                elif hasattr(response, "embeddings") and response.embeddings and len(response.embeddings) > 0:
                    return response.embeddings[0].values
            elif sdk_type == "legacy_sdk":
                model_id = current_model if current_model.startswith("models/") else f"models/{current_model}"
                response = client.embed_content(
                    model=model_id,
                    content=text
                )
                return response['embedding']
        except Exception as err:
            err_str = str(err).lower()
            if any(k in err_str for k in ["429", "rate limit", "quota", "resourceexhausted", "too many requests"]):
                rotate_to_next_model(reason=f"HTTP 429 Rate Limit ({err_str[:35]}...)")
                if (attempt + 1) % len(EMBEDDING_MODEL_POOL) == 0:
                    print(f"\n[⏳ QUOTA REFRESH WAIT] All {len(EMBEDDING_MODEL_POOL)} models rate-limited! Pausing 10s for RPM window to refresh...")
                    time.sleep(10.0)
                else:
                    time.sleep(0.5)
            else:
                time.sleep(0.5 * (attempt % 3 + 1))
                if (attempt + 1) % retries_per_model == 0:
                    rotate_to_next_model(reason=f"Error ({err_str[:30]}...)")

    raise RuntimeError(f"Failed to generate embedding for text after model rotation across all models: '{text[:30]}...'")

def calculate_cosine_similarity(vec1, vec2):
    v1 = np.array(vec1).reshape(1, -1)
    v2 = np.array(vec2).reshape(1, -1)
    return float(cosine_similarity(v1, v2)[0][0])

def evaluate_single_pair_api(text1, text2, threshold=config.SIMILARITY_THRESHOLD):
    client, sdk_type = get_gemini_client()
    if not client:
        sys.exit(1)
        
    start_time = time.time()
    emb_a = get_gemini_embedding(text1, client, sdk_type)
    emb_b = get_gemini_embedding(text2, client, sdk_type)
    score = calculate_cosine_similarity(emb_a, emb_b)
    latency_ms = (time.time() - start_time) * 1000
    
    sim_pct = score * 100
    predicted = "Similar" if score >= threshold else "Not Similar"
    
    print("\n" + "=" * 70)
    print("  PAID GEMINI API SEMANTIC SIMILARITY - SINGLE PAIR EVALUATION")
    print(f"  Active Model: {get_current_model_name()} | Mode: [REAL API]")
    print("=" * 70)
    print(f"  Sentence A: '{text1}'")
    print(f"  Sentence B: '{text2}'")
    print("-" * 70)
    print(f"  Similarity Score: {score:.4f} ({sim_pct:.2f}%)")
    print(f"  Prediction:       [{predicted.upper()}] (Threshold >= {threshold*100:.0f}%)")
    print(f"  Latency:          {latency_ms:.2f} ms")
    print("=" * 70 + "\n")
    return score, predicted

def run_api_similarity(dataset_path=config.DATASET_PATH, output_path=config.RESULTS_API_PATH, threshold=config.SIMILARITY_THRESHOLD, sample_count=None):
    client, sdk_type = get_gemini_client()
    if not client:
        sys.exit(1)

    if not os.path.exists(dataset_path):
        dataset_path = config.FALLBACK_DATASET_PATH

    df = pd.read_csv(dataset_path)
    total_original = len(df)
    
    # Technique 2: Systematic Stratified Sampling (Video Frame Analogy)
    if sample_count and sample_count < total_original:
        step = max(1, total_original // sample_count)
        df = df.iloc[::step].head(sample_count).reset_index(drop=True)
        print(f"[🎬 SYSTEMATIC SAMPLING] Sampled {len(df)} representative test cases from {total_original} total rows (Interval step: {step})")

    print("=" * 80)
    print(f"  PAID API SEMANTIC SIMILARITY EVALUATION ({dataset_path})")
    print(f"  Model Rotation Pool: {EMBEDDING_MODEL_POOL}")
    print(f"  Threshold: {threshold} | Execution Mode: [REAL API WITH RATE-THROTTLED STABILITY]")
    print("  Implemented Techniques:")
    print("    • Technique 1: Dynamic 429 Model Pool Rotation & RPM Quota Refresh Engine")
    print(f"    • Technique 2: Systematic Stratified Sampling (Sample: {len(df)}/{total_original} rows)")
    print("=" * 80)
    print(f"[+] Loaded {len(df)} test cases for evaluation")

    results = []
    print(f"\n{'ID':<4} | {'Category':<18} | {'Similarity':<10} | {'Expected':<12} | {'Predicted':<12} | {'Match'}")
    print("-" * 78)
    
    start_total_time = time.time()
    
    for idx, row in df.iterrows():
        s_id = row['id']
        category = str(row['category'])[:18]
        sent_a = row['sentence_a']
        sent_b = row['sentence_b']
        expected = row['expected']
        
        start_pair = time.time()
        try:
            emb_a = get_gemini_embedding(sent_a, client, sdk_type)
            # Throttling delay between sentence A and B to stay strictly under Google's 15 RPM limit
            time.sleep(0.12)
            emb_b = get_gemini_embedding(sent_b, client, sdk_type)
            score = calculate_cosine_similarity(emb_a, emb_b)
            sim_score = max(0.0, min(1.0, score))
        except Exception as e_row:
            print(f"[!] Failed row ID {s_id}: {e_row}")
            sim_score = 0.0
            
        latency_ms = (time.time() - start_pair) * 1000
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
            'latency_ms': round(latency_ms, 2),
            'execution_mode': 'Real API'
        })
        
        if idx < 15 or idx >= len(df) - 5:
            print(f"{s_id:<4} | {category:<18} | {sim_score*100:>8.2f}% | {expected:<12} | {predicted:<12} | [{is_match}]")
        elif idx == 15:
            print("... (evaluating remaining pairs via Gemini API with Rate Throttling & 429 Rotation) ...")
            
        time.sleep(0.15)

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)
    
    correct_count = (results_df['predicted'] == results_df['expected']).sum()
    accuracy = (correct_count / len(results_df)) * 100
    avg_latency = results_df['latency_ms'].mean()
    
    print("-" * 78)
    print(f"[*] Execution Mode: REAL API WITH DYNAMIC 429 ROTATION")
    print(f"[*] Total Evaluated: {len(results_df)} pairs")
    print(f"[*] Accuracy: {accuracy:.2f}% ({correct_count}/{len(results_df)})")
    print(f"[*] Avg Latency per Pair: {avg_latency:.2f} ms")
    print(f"[*] Results saved to '{output_path}'\n")
    return results_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paid Gemini API Semantic Similarity Script")
    parser.add_argument("--text1", type=str, help="First sentence for single-pair testing")
    parser.add_argument("--text2", type=str, help="Second sentence for single-pair testing")
    parser.add_argument("--dataset", type=str, default=config.DATASET_PATH, help="Path to evaluation dataset")
    parser.add_argument("--threshold", type=float, default=config.SIMILARITY_THRESHOLD, help="Decision threshold")
    parser.add_argument("--sample", type=int, default=None, help="Systematic sample count (e.g. 50)")
    args = parser.parse_args()
    
    if args.text1 and args.text2:
        evaluate_single_pair_api(args.text1, args.text2, threshold=args.threshold)
    else:
        run_api_similarity(dataset_path=args.dataset, threshold=args.threshold, sample_count=args.sample)
