
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.refresh_resources import refresh_resources

def manual_sync():
    print("Running Manual Synchronization...")
    print("This will check for new files AND delete vectors for missing files.")
    try:
        # We don't force refresh here, just normal refresh which now includes pruning
        results = refresh_resources(force=False)
        print(f"\nFinal results: {results}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    manual_sync()
