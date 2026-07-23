import os
import pandas as pd
from datasets import load_dataset
import config

def download_sts_benchmark(output_path=config.DATASET_PATH, num_samples=250):
    """
    Loads authentic STS-Benchmark dataset via HuggingFace datasets library.
    Contains real human-annotated similarity scores ranging from 0.0 (completely unrelated)
    to 5.0 (completely semantically equivalent).
    """
    print(f"[+] Loading authentic STS-Benchmark test split for {num_samples}+ samples...")
    ds = load_dataset("mteb/stsbenchmark-sts", split="test")
    
    records = []
    for idx, item in enumerate(ds):
        score = float(item['score'])
        expected = "Similar" if score >= 3.0 else "Not Similar"
        records.append({
            'id': idx + 1,
            'category': f"STS-B ({item['genre']})",
            'sentence_a': item['sentence1'],
            'sentence_b': item['sentence2'],
            'human_score_0_5': round(score, 2),
            'expected': expected
        })
        
    df = pd.DataFrame(records)
    print(f"[+] Total available authentic test pairs in STS-B test split: {len(df)}")
    
    # Take a balanced sample of num_samples pairs
    half_samples = num_samples // 2
    similar_df = df[df['expected'] == 'Similar'].head(half_samples)
    not_similar_df = df[df['expected'] == 'Not Similar'].head(half_samples)
    
    df_sampled = pd.concat([similar_df, not_similar_df]).reset_index(drop=True)
    df_sampled['id'] = range(1, len(df_sampled) + 1)
    
    df_sampled.to_csv(output_path, index=False)
    print(f"[+] Saved {len(df_sampled)} balanced real test cases to '{output_path}'")
    
    similar_count = (df_sampled['expected'] == 'Similar').sum()
    not_similar_count = (df_sampled['expected'] == 'Not Similar').sum()
    print(f"[*] Dataset Distribution: {similar_count} Similar pairs, {not_similar_count} Not Similar pairs.\n")
    return df_sampled

if __name__ == "__main__":
    download_sts_benchmark(num_samples=250)

