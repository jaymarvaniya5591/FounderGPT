
import os
import sys
import google.generativeai as genai
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings

def list_models():
    print(f"Using Key: {settings.GEMINI_API_KEY[:5]}...")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    print("Listing models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
