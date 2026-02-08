
import requests
import json
import time

API_URL = "http://localhost:8000"

def test_force_refresh():
    print("Testing Force Refresh API...")
    
    # 1. Get initial stats (if possible, or just rely on log output/response)
    print("Sending Force Refresh Request...")
    start_time = time.time()
    try:
        response = requests.post(
            f"{API_URL}/refresh",
            json={"force": True}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200 and response.json().get("success"):
            print("SUCCESS: Force refresh triggered successfully.")
        else:
            print("FAILURE: API returned error.")
            
    except Exception as e:
        print(f"ERROR: Could not connect to API. Is the server running? {e}")

if __name__ == "__main__":
    test_force_refresh()
