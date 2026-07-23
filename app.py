import os
import sys
import time
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import config
from semantic_local import evaluate_single_pair_local, load_local_model, calculate_cosine_similarity
from semantic_api import (
    get_gemini_client,
    get_gemini_embedding,
    get_current_model_name
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

app = Flask(__name__)
# Security Shield 1: Strict 10MB File Size Limit
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Security Shield 2: CSV Formula Injection Sanitizer
def sanitize_text(val):
    if not isinstance(val, str):
        return str(val)
    val = val.strip()
    if val.startswith(('=', '+', '-', '@', '|', '%')):
        val = "'" + val  # Escape formula prefix
    return val

@app.route('/')
def index():
    threshold_pct = f"{config.SIMILARITY_THRESHOLD * 100:.0f}%"
    return render_template('index.html', threshold_pct=threshold_pct)

@app.route('/compare', methods=['POST'])
def compare():
    try:
        data = request.get_json(silent=True) or request.form
        sentence_a = sanitize_text(data.get('sentence_a') or '')
        sentence_b = sanitize_text(data.get('sentence_b') or '')
        model_choice = (data.get('model') or 'local').strip().lower()

        if not sentence_a or not sentence_b:
            return jsonify({
                'success': False,
                'error': 'Both Sentence A and Sentence B are required. Please enter text in both fields.'
            }), 400

        threshold = getattr(config, 'SIMILARITY_THRESHOLD', 0.70)
        start_time = time.time()

        if model_choice == 'api':
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or getattr(config, "GEMINI_API_KEY", None)
            if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
                return jsonify({
                    'success': False,
                    'error': 'Gemini API Key is missing. Please set GEMINI_API_KEY in your .env file or environment variables to use Gemini API mode.'
                }), 400

            client, sdk_type = get_gemini_client()
            if not client:
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to Google Gemini API. Please verify your API key or check network availability.'
                }), 503

            emb_a = get_gemini_embedding(sentence_a, client, sdk_type)
            emb_b = get_gemini_embedding(sentence_b, client, sdk_type)
            raw_score = calculate_cosine_similarity(emb_a, emb_b)
            
            score = max(0.0, min(1.0, float(raw_score)))
            latency_ms = (time.time() - start_time) * 1000
            predicted = "Similar" if score >= threshold else "Not Similar"
            current_model = get_current_model_name()

            return jsonify({
                'success': True,
                'score': round(score, 4),
                'similarity_pct': f"{score * 100:.2f}%",
                'predicted': predicted,
                'execution_mode': f"Gemini API ({current_model})",
                'latency_ms': round(latency_ms, 2),
                'model_used': current_model,
                'threshold': threshold
            })

        else:
            raw_score, predicted = evaluate_single_pair_local(sentence_a, sentence_b, threshold=threshold)
            latency_ms = (time.time() - start_time) * 1000
            score = max(0.0, min(1.0, float(raw_score)))

            return jsonify({
                'success': True,
                'score': round(score, 4),
                'similarity_pct': f"{score * 100:.2f}%",
                'predicted': predicted,
                'execution_mode': 'Local CPU (all-MiniLM-L6-v2)',
                'latency_ms': round(latency_ms, 2),
                'model_used': config.LOCAL_MODEL_NAME,
                'threshold': threshold
            })

    except Exception as err:
        return jsonify({
            'success': False,
            'error': f"An unexpected error occurred during similarity evaluation: {str(err)}"
        }), 500

@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():
    """Secure Dataset Upload Endpoint with Full Results CSV Export Support"""
    try:
        if 'dataset_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded. Please select a .csv dataset file.'}), 400

        file = request.files['dataset_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename selected.'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Security Violation: Only authentic .csv files are allowed.'}), 400

        filename = secure_filename(file.filename)
        model_choice = (request.form.get('model') or 'local').strip().lower()

        try:
            df = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8', errors='ignore')))
        except Exception as e_parse:
            return jsonify({'success': False, 'error': f'Invalid CSV format: {str(e_parse)}'}), 400

        cols = [c.lower().strip() for c in df.columns]
        if 'sentence_a' not in cols or 'sentence_b' not in cols:
            return jsonify({
                'success': False,
                'error': 'CSV Schema Error: Dataset must contain "sentence_a" and "sentence_b" headers.'
            }), 400

        col_map = {c.lower().strip(): c for c in df.columns}
        col_a = col_map['sentence_a']
        col_b = col_map['sentence_b']

        # Process up to 500 rows in full
        df_batch = df.head(500).copy()
        threshold = getattr(config, 'SIMILARITY_THRESHOLD', 0.70)
        
        results = []
        start_batch_time = time.time()

        if model_choice == 'api':
            client, sdk_type = get_gemini_client()
            if not client:
                return jsonify({'success': False, 'error': 'Gemini API connection unavailable.'}), 503
            
            for idx, row in df_batch.iterrows():
                sa = sanitize_text(str(row[col_a]))
                sb = sanitize_text(str(row[col_b]))
                emb_a = get_gemini_embedding(sa, client, sdk_type)
                emb_b = get_gemini_embedding(sb, client, sdk_type)
                score = max(0.0, min(1.0, float(calculate_cosine_similarity(emb_a, emb_b))))
                pred = "Similar" if score >= threshold else "Not Similar"
                results.append({
                    'id': idx + 1,
                    'sentence_a': sa,
                    'sentence_b': sb,
                    'score': round(score, 4),
                    'similarity_pct': f"{score * 100:.2f}%",
                    'predicted': pred
                })
        else:
            model = load_local_model()
            all_a = [sanitize_text(str(r[col_a])) for _, r in df_batch.iterrows()]
            all_b = [sanitize_text(str(r[col_b])) for _, r in df_batch.iterrows()]
            
            embs = model.encode(all_a + all_b, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
            embs_a = embs[:len(df_batch)]
            embs_b = embs[len(df_batch):]

            for idx in range(len(df_batch)):
                score = max(0.0, min(1.0, float(calculate_cosine_similarity(embs_a[idx], embs_b[idx]))))
                pred = "Similar" if score >= threshold else "Not Similar"
                results.append({
                    'id': idx + 1,
                    'sentence_a': all_a[idx],
                    'sentence_b': all_b[idx],
                    'score': round(score, 4),
                    'similarity_pct': f"{score * 100:.2f}%",
                    'predicted': pred
                })

        total_latency = (time.time() - start_batch_time) * 1000
        avg_latency = total_latency / len(results) if results else 0

        return jsonify({
            'success': True,
            'filename': filename,
            'total_processed': len(results),
            'results': results,  # Full dataset results array for CSV download
            'preview_results': results[:50],  # UI table preview (first 50)
            'avg_latency_ms': round(avg_latency, 2),
            'execution_mode': 'Gemini API' if model_choice == 'api' else 'Local CPU'
        })

    except Exception as err:
        return jsonify({'success': False, 'error': f'Batch processing failed: {str(err)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
