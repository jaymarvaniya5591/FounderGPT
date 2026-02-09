
import os
import sys
from qdrant_client import QdrantClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.settings import settings
except ImportError:
    print("Could not import settings.")
    sys.exit(1)

def list_qdrant_contents():
    print(f"Connecting to Qdrant: {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    collection_name = settings.QDRANT_COLLECTION_NAME
    
    # Scroll through all points to aggregate data
    # Note: For very large collections, this might be slow, but suitable for this size.
    print(f"Fetching all points from collection '{collection_name}'...")
    
    points = []
    next_offset = None
    
    while True:
        # Fetch in batches
        records, next_offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=next_offset,
            with_payload=True,
            with_vectors=False
        )
        points.extend(records)
        if not next_offset:
            break
            
    print(f"Total points (chunks) found: {len(points)}")
    
    # Aggregate by source_file
    files = {}
    
    for point in points:
        payload = point.payload
        source_file = payload.get('source_file', 'unknown')
        resource_type = payload.get('resource_type', 'unknown')
        
        if source_file not in files:
            files[source_file] = {
                'count': 0,
                'type': resource_type,
                'ids': []
            }
        
        files[source_file]['count'] += 1
        files[source_file]['ids'].append(point.id)
    
    # Print report
    print(f"\n{'='*60}")
    print(f"  QDRANT CONTENTS REPORT")
    print(f"{'='*60}")
    
    # Sort by type then name
    sorted_files = sorted(files.items(), key=lambda x: (x[1]['type'], x[0]))
    
    current_type = None
    
    for filename, data in sorted_files:
        if data['type'] != current_type:
            current_type = data['type']
            print(f"\n--- {current_type.upper()}S ---")
            
        print(f"  [{data['count']} chunks] {filename}")
        
    print(f"\n{'='*60}")
    print(f"Total Unique Files: {len(files)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    list_qdrant_contents()
