import sys
import os

# Put project root in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User
from services.auth_service import verify_password
import requests

def test_api():
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()

    # Pre-clean the test user to make the test perfectly repeatable
    db = SessionLocal()
    existing_test_user = db.query(User).filter(User.phone == "7016998030").first()
    if existing_test_user:
        db.delete(existing_test_user)
        db.commit()
    db.close()

    print("--- 1. Testing Seeded Admin Login ---")
    login_data = {
        "phone": "7016998037",
        "password": "Admin@123"
    }
    resp = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Admin logged in and redirected to dashboard successfully!")
    else:
        print("[FAIL] Admin login failed.")
        sys.exit(1)

    print("\n--- 2. Testing New User Registration ---")
    register_data = {
        "name": "Fenil Patel",
        "phone": "7016998030",
        "password": "FarmerPassword@123"
    }
    resp = session.post(f"{base_url}/register", data=register_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] New user registered successfully!")
    else:
        print("[FAIL] Registration failed.")
        sys.exit(1)

    print("\n--- 3. Testing Forgot Password OTP Generation ---")
    forgot_data = {
        "phone": "7016998030"
    }
    resp = session.post(f"{base_url}/forgot-password", data=forgot_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 302 and "reset-password" in resp.headers.get("Location", ""):
        print("[SUCCESS] Forgot password OTP request succeeded and redirected to reset-password!")
    else:
        print("[FAIL] Forgot password request failed.")
        sys.exit(1)

    print("\n--- 4. Checking Database for Generated OTP ---")
    db = SessionLocal()
    user = db.query(User).filter(User.phone == "7016998030").first()
    if user and user.otp:
        print(f"[SUCCESS] OTP found in database: {user.otp} (expires at: {user.otp_expiry})")
        otp_code = user.otp
    else:
        print("[FAIL] No OTP code found in database for user.")
        db.close()
        sys.exit(1)
    db.close()

    print("\n--- 5. Testing Password Reset using OTP ---")
    reset_data = {
        "phone": "7016998030",
        "otp": otp_code,
        "password": "NewSecretPassword@123"
    }
    resp = session.post(f"{base_url}/reset-password", data=reset_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] Password reset succeeded using OTP!")
    else:
        print("[FAIL] Password reset using OTP failed.")
        sys.exit(1)

    print("\n--- 6. Testing Login with New Password ---")
    login_data_new = {
        "phone": "7016998030",
        "password": "NewSecretPassword@123"
    }
    resp = session.post(f"{base_url}/login", data=login_data_new, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Logged in with new password successfully!")
    else:
        print("[FAIL] Login with new password failed.")
        sys.exit(1)

    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! AUTHENTICATION CONVERTED TO PHONE + OTP RECOVERY WORKS!")
    print("==========================================")

if __name__ == "__main__":
    test_api()
