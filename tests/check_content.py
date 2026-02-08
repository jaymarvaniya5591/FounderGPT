
import sys
import os
from pathlib import Path
from qdrant_client import QdrantClient

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

def check_mom_test():
    print("Checking for The Mom Test...")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    scroll_result = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        limit=10,
        with_payload=True,
        with_vectors=False
    )
    
    points, _ = scroll_result
    found = False
    for p in points:
        sf = p.payload.get("source_file")
        if sf and "Mom-Test" in sf:
            found = True
            print(f"FOUND: {sf}")
            break
            
    if not found:
        print("NOT FOUND: The Mom Test vectors are missing.")
    else:
        print("Vectors exist in database.")

if __name__ == "__main__":
    check_mom_test()
