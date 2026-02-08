
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from backend.claude_client import ClaudeClient

def test_fallback():
    print("Testing Fallback Mechanism...")
    
    # 1. Force invalid Claude Key
    settings.CLAUDE_API_KEY = "invalid-key"
    
    # 2. Re-initialize Claude Client to pick up the bad key
    client = ClaudeClient()
    
    # 3. Create dummy chunks
    chunks = [
        {
            "resource_type": "book",
            "exact_text": "Founders should focus on cash flow above all else during a crisis.",
            "score": 0.9,
            "book_title": "The Hard Thing About Hard Things",
            "author": "Ben Horowitz",
            "page_number": 100
        }
    ]
    
    # 4. Make a request
    print("Sending request with INVALID Claude key...")
    result = client.generate_response("What should I do in a crisis?", chunks)
    
    # 5. Check result
    if result["success"]:
        print("\nSUCCESS: Request succeeded despite invalid Claude key!")
        print("Response preview:", result["full_response"][:100] + "...")
        print("\nFallback verified.")
    else:
        print("\nFAILURE: Request failed.")
        print("Error:", result.get("error"))

if __name__ == "__main__":
    test_fallback()
