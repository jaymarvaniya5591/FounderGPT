
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.vector_search import search_resources

def test_lean_startup_retrieval():
    print("Testing Retrieval for 'Lean Startup' concepts...")
    
    queries = [
        "What is an MVP?",
        "How do I build a minimum viable product?",
        "Build measure learn loop",
        "Eric Ries"
    ]
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        results = search_resources(q, top_k=3)
        found_lean = False
        for r in results:
            title = r.get('book_title')
            print(f" - Found: {title} (Score: {r.get('score'):.4f})")
            if title and "lean" in title.lower():
                found_lean = True
                
        if found_lean:
            print("  [SUCCESS] Found 'Lean Startup' content.")
        else:
            print("  [WARNING] Did NOT find 'Lean Startup' content.")

if __name__ == "__main__":
    test_lean_startup_retrieval()
