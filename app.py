import os
import sys
import time
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

import config
from semantic_local import evaluate_single_pair_local
from semantic_api import (
    get_gemini_client,
    get_gemini_embedding,
    calculate_cosine_similarity,
    get_current_model_name
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    threshold_pct = f"{config.SIMILARITY_THRESHOLD * 100:.0f}%"
    return render_template('index.html', threshold_pct=threshold_pct)

@app.route('/compare', methods=['POST'])
def compare():
    try:
        data = request.get_json(silent=True) or request.form
        sentence_a = (data.get('sentence_a') or '').strip()
        sentence_b = (data.get('sentence_b') or '').strip()
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
            execution_mode = f"Gemini API ({current_model})"

            return jsonify({
                'success': True,
                'score': round(score, 4),
                'similarity_pct': f"{score * 100:.2f}%",
                'predicted': predicted,
                'execution_mode': execution_mode,
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
