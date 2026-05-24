import sys
import os
import requests

# Put project root in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_market():
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()

    print("--- 1. Testing Unauthenticated Access to /market ---")
    resp = session.get(f"{base_url}/market", allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] Unauthenticated request correctly redirected to login page!")
    else:
        print("[FAIL] Unauthenticated request security gate failed.")
        sys.exit(1)

    print("\n--- 2. Logging in with Seeded Admin Account ---")
    login_data = {
        "phone": "7016998037",
        "password": "Admin@123"
    }
    resp = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Logged in successfully!")
    else:
        print("[FAIL] Login failed.")
        sys.exit(1)

    print("\n--- 3. Testing Authenticated Access to /market ---")
    resp = session.get(f"{base_url}/market")
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("[SUCCESS] Successfully accessed /market dashboard while logged in!")
    else:
        print("[FAIL] Failed to access /market dashboard.")
        sys.exit(1)

    print("\n--- 4. Checking Page Content for Mandi & Weather Dash Elements ---")
    html_content = resp.text
    indicators = [
        "Mandi Market & Weather Dashboard",
        "Region Weather Forecast",
        "APMC Live Mandi Rates",
        "weatherRegion",
        "mandiSearch"
    ]
    all_found = True
    for ind in indicators:
        if ind in html_content:
            print(f"[OK] Found indicator: '{ind}'")
        else:
            print(f"[FAIL] Missing indicator: '{ind}'")
            all_found = False
            
    if all_found:
        print("[SUCCESS] All required visual and functional components exist in the HTML template!")
    else:
        print("[FAIL] Visual components check failed.")
        sys.exit(1)

    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! BILINGUAL MANDI & WEATHER DASHBOARD IMPLEMENTED & SECURED!")
    print("==========================================")

if __name__ == "__main__":
    test_market();
