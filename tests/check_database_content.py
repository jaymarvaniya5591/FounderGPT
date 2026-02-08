
import sys
import os
from pathlib import Path
from qdrant_client import QdrantClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

def check_database_content():
    print("Checking Qdrant Content...")
    try:
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        # Scroll through points to simulate listing unique books
        # Note: This is inefficient for large DBs but fine for debugging small ones
        print(f"Collection: {settings.QDRANT_COLLECTION_NAME}")
        
        books = set()
        articles = set()
        total_points = 0
        
        offset = None
        while True:
            scroll_result = client.scroll(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                scroll_filter=None,
                limit=100,
                with_payload=True,
                with_vectors=False,
                offset=offset
            )
            
            points, next_offset = scroll_result
            if not points:
                break
                
            total_points += len(points)
            for point in points:
                payload = point.payload
                if payload.get("resource_type") == "book":
                    books.add(payload.get("book_title") or payload.get("source_file"))
                elif payload.get("resource_type") == "article":
                    articles.add(payload.get("article_title") or payload.get("source_file"))
            
            offset = next_offset
            if offset is None:
                break
        
        print(f"\nTotal Chunks: {total_points}")
        print(f"Unique Books Found: {len(books)}")
        for b in books:
            print(f" - {b}")
            
        print(f"Unique Articles Found: {len(articles)}")
        for a in articles:
            print(f" - {a}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_database_content()
