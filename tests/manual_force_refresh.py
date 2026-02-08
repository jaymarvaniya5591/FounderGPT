
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.refresh_resources import refresh_resources

def manual_force_refresh():
    print("Running Manual Force Refresh...")
    try:
        # Pass force=True
        results = refresh_resources(force=True)
        print(f"\nFinal results: {results}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    manual_force_refresh()
