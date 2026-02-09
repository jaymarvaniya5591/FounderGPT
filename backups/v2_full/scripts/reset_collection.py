"""
Reset Collection Script
Deletes the existing Qdrant collection and recreates it with 1024 dimensions
for Cohere embed-english-v3.0 embeddings.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from config.settings import settings


def reset_collection():
    """Delete and recreate the Qdrant collection with new dimensions."""
    print(f"Connecting to Qdrant: {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    collection_name = settings.QDRANT_COLLECTION_NAME
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if collection_name in collection_names:
        print(f"Deleting existing collection: {collection_name}")
        client.delete_collection(collection_name=collection_name)
        print("  Collection deleted successfully!")
    else:
        print(f"Collection '{collection_name}' does not exist, nothing to delete.")
    
    # Create new collection with 1024 dimensions
    print(f"\nCreating new collection: {collection_name}")
    print(f"  Dimension: {settings.EMBEDDING_DIMENSION}")
    print(f"  Distance: COSINE")
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.EMBEDDING_DIMENSION,
            distance=Distance.COSINE
        )
    )
    
    # Create indexes for filtering
    print("Creating payload indexes...")
    client.create_payload_index(
        collection_name=collection_name,
        field_name="source_file",
        field_schema="keyword"
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="resource_type",
        field_schema="keyword"
    )
    
    print("\n[SUCCESS] Collection reset complete!")
    print(f"  New collection '{collection_name}' created with {settings.EMBEDDING_DIMENSION} dimensions")
    
    # Also clear the processed files tracker
    processed_files_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        settings.PROCESSED_FILES_PATH
    )
    if os.path.exists(processed_files_path):
        os.remove(processed_files_path)
        print(f"  Cleared processed files tracker: {processed_files_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("QDRANT COLLECTION RESET")
    print("=" * 50)
    print(f"\nThis will DELETE all existing vectors and recreate the collection")
    print(f"with {settings.EMBEDDING_DIMENSION}-dimensional vectors for Cohere embeddings.\n")
    
    # Auto-proceed without confirmation
    reset_collection()
