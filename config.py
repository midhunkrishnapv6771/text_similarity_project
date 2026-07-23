"""
Centralized Configuration for Text Similarity Benchmark Project
Supports environment overrides from .env with sensible fallback defaults.
"""
import os
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Decision Threshold for Binary Classification (Similar vs Not Similar)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.70"))

# Dataset Paths
DATASET_PATH = os.getenv("DATASET_PATH", "dataset_real_sts.csv")
FALLBACK_DATASET_PATH = "dataset.csv"

# Result Output File Paths
RESULTS_LOCAL_PATH = os.getenv("RESULTS_LOCAL_PATH", "results_local.csv")
RESULTS_API_PATH = os.getenv("RESULTS_API_PATH", "results_api.csv")
RESULTS_COMPARISON_PATH = os.getenv("RESULTS_COMPARISON_PATH", "results_comparison.csv")
COMPARISON_REPORT_PATH = "comparison_report.md"

# Model Identification
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "google/gemini-embedding-001")
LEXICAL_MODEL_NAME = "rapidfuzz/token_sort_ratio"
