''''src/test.py'''
import requests
import json
import sys
from dotenv import load_dotenv
import os
from pathlib import Path
# Load variables from .env into os.environ
BASE_ADDR = Path(__file__).parent.parent
ENV_FILE = BASE_ADDR / '.env'
load_dotenv(ENV_FILE)
OLLAMA_URL = OLLAMAURL
DEFAULT_MODEL = MODEL   # <-- changed to your available model

def get_available_models():
    """Return a list of installed model names."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        return [m['name'] for m in resp.json().get('models', [])]
    except Exception as e:
        print(f"⚠️  Could not fetch model list: {e}", file=sys.stderr)
        return []

def generate_text(prompt, model=None, stream=False):
    """
    Generate text using a specific model.
    If model is None, use the first available one (or DEFAULT_MODEL).
    """
    if model is None:
        models = get_available_models()
        if models:
            model = models[0]      # pick first installed
        else:
            model = DEFAULT_MODEL  # fallback to our default

    print(f"🧠 Using model: {model}")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }

    try:
        if stream:
            with requests.post(f"{OLLAMA_URL}/api/generate",
                               json=payload,
                               stream=True,
                               timeout=60) as resp:
                resp.raise_for_status()
                print("📝 Response (streaming):")
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        print(chunk['response'], end='', flush=True)
                print()  # newline after stream
        else:
            resp = requests.post(f"{OLLAMA_URL}/api/generate",
                                 json=payload,
                                 timeout=60)
            resp.raise_for_status()
            result = resp.json()
            print(f"📝 Response: {result['response']}")

    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            available = get_available_models()
            print(f"❌ Model '{model}' not found.")
            if available:
                print(f"   Available: {', '.join(available)}")
            else:
                print("   No models installed. Run `ollama pull <model>`.")
        else:
            print(f"❌ HTTP error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def chat(prompt, model=None):
    """Chat using the /api/chat endpoint (conversational)."""
    if model is None:
        models = get_available_models()
        model = models[0] if models else DEFAULT_MODEL

    print(f"🧠 Using model: {model}")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        print(f"💬 Assistant: {result['message']['content']}")
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            print(f"❌ Model '{model}' not found for chat.")
        else:
            print(f"❌ HTTP error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # 1. List available models
    models = get_available_models()
    print(f"📦 Installed models: {models if models else 'None'}")

    print("\n" + "=" * 50)

    # 2. Generate without streaming (uses first installed model)
    generate_text("What is the capital of France?", stream=False)

    print("\n" + "=" * 50)

    # 3. Generate with streaming (explicitly use llama3.1:8b)
    generate_text("Write a haiku about AI", model="llama3.1:8b", stream=True)

    print("\n" + "=" * 50)

    # 4. Chat example (uses first installed model)
    chat("Explain machine learning in one sentence.")
