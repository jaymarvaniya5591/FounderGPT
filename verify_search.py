
from backend.vector_search import vector_search
import json

query = "i am thinking of an idea. it helps bridge gap between kirana stores and d2c brands. i have validated by talking to d2c brands that it is problem for them and logically i think it makes sense for kirana stores too. should i go ahead with the product?"

print(f"Running search for query: {query[:50]}...")
results = vector_search.search(query)

print(f"\nFound {len(results)} results (Expected: 16).")

if len(results) == 16:
    print("[SUCCESS] correct number of results returned.")
else:
    print(f"[WARNING] Expected 16 results but got {len(results)}")

found = False
for i, result in enumerate(results):
    text = result.get('exact_text', '')
    score = result.get('score', 0)
    source = result.get('source_file', 'Unknown')
    
    if "LaunchBit" in text:
        found = True
        print(f"\n[SUCCESS] Found LaunchBit story at rank {i+1} with score {score:.4f}")
        print(f"Source: {source}")
        print(f"Snippet: {text[:100]}...")
        break

if not found:
    print("\n[FAILURE] LaunchBit story STILL NOT FOUND in top results.")
    print("Top 3 results:")
    for i, result in enumerate(results[:3]):
        print(f"{i+1}. [{result.get('score', 0):.4f}] {result.get('exact_text', '')[:50]}...")
