"""
Utility Script: List All Available Google Gemini Models & Embedding Capabilities
"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def list_all_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
        print("\n" + "!" * 75)
        print("  [!] ERROR: NO API KEY FOUND IN .env")
        print("  Please add your GEMINI_API_KEY to your .env file first.")
        print("!" * 75 + "\n")
        return

    print("=" * 80)
    print(f"  FETCHING AVAILABLE GOOGLE GEMINI MODELS (Key Prefix: {api_key[:6]}...)")
    print("=" * 80)

    model_list = []
    
    # 1. Try google-genai (New SDK)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m in client.models.list():
            name = getattr(m, 'name', str(m))
            display_name = getattr(m, 'display_name', '')
            methods = getattr(m, 'supported_actions', []) or getattr(m, 'supported_generation_methods', [])
            model_list.append({
                'Model ID': name,
                'Display Name': display_name,
                'Supported Methods': ", ".join(methods) if isinstance(methods, list) else str(methods)
            })
        sdk_used = "google-genai"
    except Exception as e1:
        # 2. Fallback to google.generativeai (Legacy SDK)
        try:
            import google.generativeai as genai_leg
            genai_leg.configure(api_key=api_key)
            for m in genai_leg.list_models():
                model_list.append({
                    'Model ID': m.name,
                    'Display Name': m.display_name,
                    'Supported Methods': ", ".join(m.supported_generation_methods)
                })
            sdk_used = "google.generativeai"
        except Exception as e2:
            print("\n" + "!" * 80)
            print("  [!] FAILED TO LIST MODELS FROM GEMINI API SERVER.")
            print(f"  google-genai Error: {e1}")
            print(f"  google.generativeai Error: {e2}")
            print("!" * 80 + "\n")
            return

    if not model_list:
        print("[!] No models returned from API server.")
        return

    df_models = pd.DataFrame(model_list)
    print(f"\n[+] Successfully retrieved {len(df_models)} models via {sdk_used}:\n")
    
    # Display Embedding Models first
    embed_models = df_models[df_models['Model ID'].str.contains('embed', case=False, na=False)]
    gen_models = df_models[~df_models['Model ID'].str.contains('embed', case=False, na=False)]
    
    print("--- 📌 EMBEDDING MODELS ---")
    if len(embed_models) > 0:
        for idx, row in embed_models.iterrows():
            print(f"  • Model ID:     {row['Model ID']}")
            print(f"    Display Name: {row['Display Name']}")
            print(f"    Methods:      {row['Supported Methods']}\n")
    else:
        print("  None found.\n")
        
    print("--- 📌 GENERATION & CHAT MODELS ---")
    for idx, row in gen_models.head(10).iterrows():
        print(f"  • Model ID:     {row['Model ID']}")
        print(f"    Display Name: {row['Display Name']}")
        print(f"    Methods:      {row['Supported Methods']}\n")
        
    if len(gen_models) > 10:
        print(f"  ... and {len(gen_models) - 10} more generation models.")
        
    print("=" * 80)

if __name__ == "__main__":
    list_all_gemini_models()
