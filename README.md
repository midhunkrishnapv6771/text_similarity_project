# Semantic Text Similarity Benchmark & Flask Application

A production-ready NLP benchmarking platform and web application comparing **Local Open-Source Sentence Embeddings** (`sentence-transformers/all-MiniLM-L6-v2`), a **Paid Cloud Semantic API** (Google Gemini `gemini-embedding-001`), and **Lexical Baselines** on authentic human-annotated STS-B test cases.

---

## 🌟 Dual Execution Modes

This repository operates in **two independent, fully decoupled execution modes**:

1. **Flask Web Application Mode (`app.py`)**:
   A modern, single-page web interface allowing users to input sentence pairs, choose between Local or Gemini API embedding engines, inspect similarity percentages, latency metrics, and execution modes in real-time.

2. **Research Benchmark & Evaluation Mode (`evaluator.py`)**:
   A comprehensive evaluation engine executing full dataset benchmarks, dynamic HTTP 429 rate-limit failovers, systematic stratified sampling, and empirical grid-search weight optimization across 250 STS-B pairs.

---

## 💡 System Architecture

```text
                                  ┌───────────────────────────┐
                                  │         config.py         │
                                  │ (THRESHOLD=0.70, .env)    │
                                  └─────────────┬─────────────┘
                                                │
           ┌────────────────────────────────────┴────────────────────────────────────┐
           │                                                                         │
           ▼                                                                         ▼
┌───────────────────────────┐                                             ┌───────────────────────────┐
│       app.py (Flask)      │                                             │       evaluator.py        │
│   (Web User Interface)    │                                             │   (Benchmark Suite)       │
└─────────────┬─────────────┘                                             └─────────────┬─────────────┘
              │                                                                         │
              ├────────────────────────────────────┬────────────────────────────────────┤
              ▼                                    ▼                                    ▼
┌───────────────────────────┐        ┌───────────────────────────┐        ┌───────────────────────────┐
│     semantic_local.py     │        │      semantic_api.py      │        │     dataset_real_sts.csv  │
│ (sentence-transformers)   │        │ (Gemini Embedding + 429)  │        │   (250 STS-B Test Pairs)  │
└───────────────────────────┘        └───────────────────────────┘        └───────────────────────────┘
```

---

## ⚡ Features & Production Capabilities

- **Dual Embedding Support**: Switch seamlessly between local CPU sentence-transformers and Google Gemini Cloud API embeddings.
- **HTTP 429 Dynamic Model Rotation**: Automatic failover across model pools (`gemini-embedding-001` $\rightarrow$ `gemini-embedding-2` $\rightarrow$ `gemini-embedding-2-preview`) to guarantee zero-crash execution.
- **Interactive UI Extras**:
  - 🌙 **Dark / Light Mode Toggle** (with persistent `localStorage` preference).
  - 🔄 **Swap Sentences Button** for quick bidirectional comparisons.
  - 📋 **Copy Result Button** for instant clipboard sharing.
  - ⚡ **Keyboard Shortcut**: Press `Ctrl + Enter` (or `Cmd + Enter`) inside textareas to evaluate immediately.
  - 📊 **Live Character Counter** & **Preset Example Picker**.
- **Industry-Standard Metrics**: Powered by `scikit-learn` (`accuracy_score`, `precision_score`, `recall_score`, `f1_score`, `confusion_matrix`).
- **Render-Ready Deployment**: Includes `gunicorn` configuration, environment variable support, and production WSGI entry point.

---

## 📁 Repository Structure

```text
text_similarity_project/
├── app.py                  # Production Flask Web Server (GET / , POST /compare)
├── config.py               # Central configuration (Threshold=0.70, Paths, .env)
├── semantic_local.py       # Local Sentence-Transformers engine (Batch Encoded)
├── semantic_api.py         # Paid Gemini API engine (429 Model Rotation + Rate-Throttled)
├── evaluator.py            # Evaluation & metrics engine (scikit-learn + Grid Search)
├── list_gemini_models.py   # Live Google Gemini model listing utility
├── dataset_real_sts.csv    # 250 authentic human-annotated STS-B test cases
├── dataset_uncertain_cases.csv # Exported hard test cases (<90% local similarity)
├── templates/
│   └── index.html          # Modern HTML5 responsive template
├── static/
│   ├── css/
│   │   └── style.css       # Vanilla CSS design system with CSS custom properties
│   └── js/
│       └── app.js          # JavaScript controller & AJAX fetch pipeline
├── results_local.csv       # Local execution outputs
├── results_api.csv         # API execution outputs
├── results_comparison.csv  # Combined comparative dataset with optimal ensemble scores
├── comparison_report.md    # In-depth benchmark analysis report
├── requirements.txt        # Project dependencies (Flask, Gunicorn, Torch, etc.)
└── README.md               # Setup guide & API documentation
```

---

## 🚀 Quick Start & Local Setup

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/midhunkrishnapv6771/text_similarity_project.git
cd text_similarity_project

# Create & activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Create & activate virtual environment (Linux / macOS)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Optional: Set Gemini API key for Cloud API mode
GEMINI_API_KEY=your_google_gemini_api_key_here

# Optional: Override decision threshold (Default = 0.70)
SIMILARITY_THRESHOLD=0.70
```

---

## 💻 Running the Application

### Mode 1: Run Flask Web Application

```bash
python app.py
```
Open your browser at: `http://localhost:5000`

### Mode 2: Run Research Benchmark Suite

```bash
# Evaluate Local Model
python semantic_local.py

# Evaluate Paid Gemini API
python semantic_api.py

# Run Full Comparative Evaluation & Grid Search Optimization
python evaluator.py
```

---

## 📡 API Endpoint Reference

### `POST /compare`

Calculates semantic similarity between two sentences using the selected model engine.

#### Request Payload (`application/json`):
```json
{
  "sentence_a": "A plane is taking off from the runway.",
  "sentence_b": "An airplane is ascending into the sky.",
  "model": "local"
}
```

#### Response (`application/json`):
```json
{
  "success": true,
  "score": 0.8786,
  "similarity_pct": "87.86%",
  "predicted": "Similar",
  "execution_mode": "Local CPU (all-MiniLM-L6-v2)",
  "latency_ms": 3.12,
  "model_used": "sentence-transformers/all-MiniLM-L6-v2",
  "threshold": 0.70
}
```

---

## 🌐 Deploying to Render

To deploy this Flask application to **[Render](https://render.com/)**:

1. **Push Code to GitHub**:
   Ensure your repository contains `app.py`, `requirements.txt`, `templates/`, and `static/`.

2. **Create New Web Service on Render**:
   - Connect your GitHub repository.
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

3. **Add Environment Variables on Render Dashboard**:
   - Key: `GEMINI_API_KEY`, Value: `<Your_Google_AI_Studio_Key>`
   - Key: `PYTHON_VERSION`, Value: `3.10.11`

4. **Deploy**: Render will automatically build the container and deploy your live URL (e.g., `https://text-similarity-app.onrender.com`).

---

## 📷 Application Screenshot

```text
+-----------------------------------------------------------------------------------+
|  ⚡ Semantic Text Similarity                                           [ 🌙 Dark ] |
|  Real-time NLP Embedding Benchmark Platform                                       |
|-----------------------------------------------------------------------------------|
|  Try Example Pair: [ 1. High Similarity: Plane taking off ▼ ]    [ 🔄 Swap ]       |
|                                                                                   |
|  Sentence A (42 chars)                       Sentence B (48 chars)                |
|  +---------------------------------------+  +-----------------------------------+ |
|  | A plane is taking off from runway...  |  | An airplane is ascending into...  | |
|  +---------------------------------------+  +-----------------------------------+ |
|                                                                                   |
|  Embedding Model Engine:                                                          |
|  (•) Local Model (MiniLM-L6-v2)     ( ) Gemini API (Cloud)                        |
|                                                                                   |
|                                            [  Compare Sentences  ]  (Ctrl+Enter)  |
|-----------------------------------------------------------------------------------|
|  SIMILARITY SCORE          PREDICTION        EXECUTION MODE          LATENCY      |
|  87.86% [██████████░░]     [ SIMILAR ]       Local CPU (MiniLM)      3.12 ms      |
+-----------------------------------------------------------------------------------+
```

---

## 📊 Benchmark Summary Matrix (scikit-learn 1.0+)

| Metric | Lexical (Fuzz) | Local Model (`all-MiniLM-L6-v2`) | Paid API (`Gemini gemini-embedding-001`) | Optimal Ensemble (40/60) 🏆 |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy (%)** | 61.20% | 86.00% | 64.00% | **88.00% 🏆** |
| **Precision (%)** | 66.28% | **88.14%** | 58.14% | 80.65% |
| **Recall (%)** | 45.60% | 83.20% | **100.00%** | **100.00% 🏆** |
| **F1-Score (%)** | 54.03% | 85.60% | 73.53% | **89.29% 🏆** |
| **Avg Latency** | **< 0.5 ms** | **4.02 ms** | 1331.31 ms | 1331.31 ms |

## 👤 Author

- **Developer**: Midhun Krishna ([@midhunkrishnapv6771](https://github.com/midhunkrishnapv6771))
- *Single-Developer Independent Project*

---

## 📜 License

MIT License &copy; 2026 - Text Similarity Research & Web Application Suite.

