
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

def inspect_payloads():
    print("Inspecting Payloads for 'the-lean-startup.pdf'...")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    # Filter for this specific file
    scroll_result = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="source_file",
                    match=MatchValue(value="the-lean-startup.pdf")
                )
            ]
        ),
        limit=5,
        with_payload=True
    )
    
    points, _ = scroll_result
    
    if not points:
        print("NO POINTS FOUND for this file!")
        return
        
    print(f"Found {len(points)} sample points.")
    for i, p in enumerate(points):
        print(f"\n--- Point {i+1} ---")
        print(f"Book: {p.payload.get('book_title')}")
        print(f"Author: {p.payload.get('author')}")
        print(f"Text Preview: {p.payload.get('exact_text')[:200]}...")

if __name__ == "__main__":
    inspect_payloads()
