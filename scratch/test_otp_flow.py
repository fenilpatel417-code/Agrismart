import sys
import os
import requests

# Put project root in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User, OTPVerification
from services.otp_service import hash_otp

def test_otp_flow():
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    test_mobile = "9876543210"

    print("=== CLEANING DATABASE FOR REPEATABILITY ===")
    db = SessionLocal()
    # Delete user and otp records for our test mobile
    db.query(User).filter((User.phone == test_mobile) | (User.mobile == test_mobile)).delete()
    db.query(OTPVerification).filter(OTPVerification.mobile == test_mobile).delete()
    db.commit()
    db.close()
    print("[OK] Cleaned test mobile records.")

    # 1. Registration Step 1
    print("\n--- 1. Testing Registration Step 1 (/register POST) ---")
    reg_data = {
        "name": "Fenil Test",
        "phone": test_mobile,
        "password": "FarmerPassword@123"
    }
    # Note: Uvicorn doesn't run with session middleware automatically unless configured, but our FastAPI main app has SessionMiddleware!
    resp = session.post(f"{base_url}/register", data=reg_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and resp.headers.get("Location") == "/verify-otp":
        print("[SUCCESS] Registration step 1 succeeded! Redirected to /verify-otp.")
    else:
        print("[FAIL] Registration step 1 failed.")
        sys.exit(1)

    # 2. Check DB for registration OTP
    print("\n--- 2. Retrieving OTP from Database ---")
    db = SessionLocal()
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.mobile == test_mobile,
        OTPVerification.purpose == "register",
        OTPVerification.is_used == 0
    ).first()
    
    if otp_record:
        print(f"[SUCCESS] Hashed OTP found in DB: {otp_record.otp_hash}")
        # Since OTP is hashed in DB, we'll look at the stdout of our server, OR for the sake of the programmatic test
        # we can bypass the hash by creating a mock OTP entry or querying it.
        # But wait! Our test script can just retrieve the logged OTP from our terminal sandbox logic, or since we are running locally
        # and writing the script, wait! We can bypass by looking at the DB or we can read what was generated.
        # Wait, in a test environment, how do we get the raw OTP?
        # Let's inspect the otp_verification database table. Oh, wait! The otp_hash is hashed, so we can't reverse it.
        # But we can override/write a known OTP in the database for the sake of testing verification!
        # Yes! Let's insert a known OTP record directly into the DB with a known raw OTP "123456" so we can test verification!
        known_otp = "123456"
        otp_record.otp_hash = hash_otp(known_otp)
        db.commit()
        print(f"[OK] Overrode OTP in database to known value: '{known_otp}' for testing.")
    else:
        print("[FAIL] No active registration OTP found in DB.")
        db.close()
        sys.exit(1)
    db.close()

    # 3. Registration Step 2: Verify OTP
    print("\n--- 3. Testing Registration Step 2 (/verify-otp POST) ---")
    verify_data = {
        "otp1": "1",
        "otp2": "2",
        "otp3": "3",
        "otp4": "4",
        "otp5": "5",
        "otp6": "6"
    }
    resp = session.post(f"{base_url}/verify-otp", data=verify_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] OTP verification succeeded! Redirected to login.")
    else:
        print("[FAIL] OTP verification failed.")
        sys.exit(1)

    # 4. Verify User is Created and is_verified = 1
    print("\n--- 4. Checking User Database State ---")
    db = SessionLocal()
    user = db.query(User).filter(User.mobile == test_mobile).first()
    if user and user.is_verified == 1:
        print(f"[SUCCESS] User '{user.name}' successfully created and marked is_verified=1!")
    else:
        print("[FAIL] User not created or not verified in database.")
        db.close()
        sys.exit(1)
    db.close()

    # 5. Forgot Password Step 1
    print("\n--- 5. Testing Forgot Password Step 1 (/forgot-password POST) ---")
    resp = session.post(f"{base_url}/forgot-password", data={"phone": test_mobile}, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and resp.headers.get("Location") == "/verify-forgot-otp":
        print("[SUCCESS] Forgot password request succeeded! Redirected to /verify-forgot-otp.")
    else:
        print("[FAIL] Forgot password request failed.")
        sys.exit(1)

    # 6. Retrieve recovery OTP
    print("\n--- 6. Overriding Recovery OTP in Database for Testing ---")
    db = SessionLocal()
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.mobile == test_mobile,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == 0
    ).first()
    
    if otp_record:
        known_recovery_otp = "654321"
        otp_record.otp_hash = hash_otp(known_recovery_otp)
        db.commit()
        print(f"[OK] Overrode recovery OTP in database to: '{known_recovery_otp}' for testing.")
    else:
        print("[FAIL] No active recovery OTP found in DB.")
        db.close()
        sys.exit(1)
    db.close()

    # 7. Verify Forgot Password OTP
    print("\n--- 7. Testing Forgot Password OTP Verification (/verify-forgot-otp POST) ---")
    verify_forgot_data = {
        "otp": known_recovery_otp
    }
    resp = session.post(f"{base_url}/verify-forgot-otp", data=verify_forgot_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and resp.headers.get("Location") == "/reset-password":
        print("[SUCCESS] Recovery OTP verification succeeded! Redirected to /reset-password.")
    else:
        print("[FAIL] Recovery OTP verification failed.")
        sys.exit(1)

    # 8. Reset Password
    print("\n--- 8. Testing Password Reset (/reset-password POST) ---")
    reset_data = {
        "password": "NewFarmerPassword@123",
        "confirm_password": "NewFarmerPassword@123"
    }
    resp = session.post(f"{base_url}/reset-password", data=reset_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Location Header: {resp.headers.get('Location')}")
    if resp.status_code == 302 and "login" in resp.headers.get("Location", ""):
        print("[SUCCESS] Password reset completed successfully!")
    else:
        print("[FAIL] Password reset failed.")
        sys.exit(1)

    # 9. Test login with new password
    print("\n--- 9. Testing Login with New Password (/login POST) ---")
    login_data = {
        "phone": test_mobile,
        "password": "NewFarmerPassword@123"
    }
    resp = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    if resp.status_code == 302 and "dashboard" in resp.headers.get("Location", ""):
        print("[SUCCESS] Successfully logged in with the new password!")
    else:
        print("[FAIL] Login failed with new password.")
        sys.exit(1)

    print("\n=======================================================")
    print("  ALL OTP INTEGRATION FLOW TESTS PASSED SUCCESSFULLY!  ")
    print("=======================================================")

if __name__ == "__main__":
    test_otp_flow()
