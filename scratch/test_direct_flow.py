import sys
import os
import requests

# Put project root in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User

def test_direct_flow():
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    test_email = "fenil.test@gmail.com"

    print("=== CLEANING DATABASE FOR REPEATABILITY ===")
    db = SessionLocal()
    # Delete test user if exists
    db.query(User).filter(User.email == test_email).delete()
    db.commit()
    db.close()
    print("[OK] Cleaned test user records.")

    # 1. Direct Registration
    print("\n--- 1. Testing Direct Registration (/register POST) ---")
    reg_data = {
        "name": "Fenil Direct",
        "email": test_email,
        "password": "FarmerPassword@123"
    }
    resp = session.post(f"{base_url}/register", data=reg_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] Direct registration succeeded! Redirected to login.")
    else:
        print("[FAIL] Direct registration failed.")
        sys.exit(1)

    # 2. Verify User Created directly
    print("\n--- 2. Verifying User Record in Database ---")
    db = SessionLocal()
    user = db.query(User).filter(User.email == test_email).first()
    if user and user.email == test_email:
        print(f"[SUCCESS] User record successfully created directly in DB: {user.name} ({user.email})")
    else:
        print("[FAIL] User not created directly in database.")
        db.close()
        sys.exit(1)
    db.close()

    # 3. Test Login with newly registered Email
    print("\n--- 3. Testing Login with New Email (/login POST) ---")
    login_data = {
        "phone": test_email,
        "password": "FarmerPassword@123"
    }
    resp = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Successfully logged in using Email!")
    else:
        print("[FAIL] Login with Email failed.")
        sys.exit(1)

    # 4. Test Login with existing Admin Phone (Backward Compatibility check)
    print("\n--- 4. Testing Login with Seeded Admin Phone (Backward Compatibility) ---")
    admin_login_data = {
        "phone": "7016998037",
        "password": "Admin@123"
    }
    admin_session = requests.Session()
    resp = admin_session.post(f"{base_url}/login", data=admin_login_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Backward compatibility verified! Logged in with Admin Phone successfully!")
    else:
        print("[FAIL] Login with Admin Phone failed.")
        sys.exit(1)

    # 5. Test Direct Password Reset using Email
    print("\n--- 5. Testing Direct Password Reset using Email (/forgot-password POST) ---")
    reset_data = {
        "email": test_email,
        "password": "NewDirectPassword@123",
        "confirm_password": "NewDirectPassword@123"
    }
    resp = session.post(f"{base_url}/forgot-password", data=reset_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] Direct password reset succeeded using Email!")
    else:
        print("[FAIL] Direct password reset failed.")
        sys.exit(1)

    # 6. Test Login with New Password
    print("\n--- 6. Testing Login with New Password (/login POST) ---")
    login_data_new = {
        "phone": test_email,
        "password": "NewDirectPassword@123"
    }
    new_session = requests.Session()
    resp = new_session.post(f"{base_url}/login", data=login_data_new, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Logged in with new password successfully!")
    else:
        print("[FAIL] Login with new password failed.")
        sys.exit(1)

    print("\n=======================================================")
    print("  ALL DIRECT FLOW INTEGRATION TESTS PASSED SUCCESSFULLY!  ")
    print("=======================================================")

if __name__ == "__main__":
    test_direct_flow()
