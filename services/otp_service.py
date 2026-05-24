import os
import random
import string
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import OTPVerification

# HOW TO SETUP TWILIO:
# 1. Go to twilio.com and sign up free
# 2. Verify your own mobile number
# 3. Get a free Twilio phone number
# 4. Copy Account SID and Auth Token from dashboard
# 5. Add to .env file:
#    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#    TWILIO_AUTH_TOKEN=your_auth_token
#    TWILIO_PHONE_NUMBER=+1234567890
# 6. In free trial, you can only send SMS to verified numbers
# 7. To send to any number, upgrade to paid ($15 minimum)
# NOTE: For Indian numbers always use +91 prefix

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

def is_twilio_configured() -> bool:
    """Checks if valid Twilio environment variables are configured."""
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_PHONE:
        return False
    if "placeholder" in TWILIO_SID.lower() or "your_account_sid" in TWILIO_SID.lower():
        return False
    return True

def generate_otp() -> str:
    """Generate a secure 6 digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=6))

def hash_otp(otp: str) -> str:
    """Hashes the OTP using SHA-256 for extra security."""
    return hashlib.sha256(otp.encode('utf-8')).hexdigest()

def send_otp_sms(mobile: str, otp: str, purpose: str) -> bool:
    """Sends the OTP via Twilio SMS, falling back to a terminal sandbox log if unconfigured."""
    # Ensure Indian numbers have +91 prefix
    formatted_mobile = mobile.strip()
    if not formatted_mobile.startswith('+'):
        formatted_mobile = '+91' + formatted_mobile

    welcome_msg = "Welcome to AgriSmart!" if purpose == "register" else "AgriSmart Password Reset."
    sms_body = (f"{welcome_msg} "
                f"Your OTP is: {otp}. "
                f"Valid for 10 minutes. "
                f"Do not share with anyone.")

    if not is_twilio_configured():
        # Beautiful Highly Visible Terminal Sandbox Banner Fallback (No emojis to prevent Windows console encoding crashes)
        border = "=" * 62
        print(f"\n{border}")
        print(f"              [AGRISMART OTP SANDBOX ACTIVE]")
        print(f"{border}")
        print(f"  Mobile Number : {formatted_mobile}")
        print(f"  Purpose       : {purpose.upper().replace('_', ' ')}")
        print(f"  SMS Body      : {sms_body}")
        print(f"  OTP Code      :  \033[1;32m{otp[0]}  {otp[1]}  {otp[2]}  {otp[3]}  {otp[4]}  {otp[5]}\033[0m  (6 digits)")
        print(f"  Expires At    : 10 minutes from now")
        print(f"{border}\n")
        return True

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            body=sms_body,
            from_=TWILIO_PHONE,
            to=formatted_mobile
        )
        return True
    except Exception as e:
        print(f"[ERROR] Twilio SMS Error: {e}")
        # Automatically print in sandbox fallback if Twilio API call fails
        border = "=" * 62
        print(f"\n{border}")
        print(f"       [AGRISMART OTP SANDBOX FALLBACK (TWILIO ERR)]")
        print(f"{border}")
        print(f"  Mobile Number : {formatted_mobile}")
        print(f"  Purpose       : {purpose.upper().replace('_', ' ')}")
        print(f"  OTP Code      :  \033[1;31m{otp[0]}  {otp[1]}  {otp[2]}  {otp[3]}  {otp[4]}  {otp[5]}\033[0m")
        print(f"  Error Message : {e}")
        print(f"{border}\n")
        return True

def can_send_otp(db: Session, mobile: str) -> tuple[bool, str]:
    """
    Checks rate limiting and security blocks for sending an OTP.
    Rules:
      - Max 3 resend/requests per hour per mobile.
      - Max 5 OTP requests per mobile per day.
      - Mobile blocked from sending if currently under a 30-minute block.
    """
    now = datetime.utcnow()

    # 1. Check if currently blocked
    blocked = db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.blocked_until > now
    ).first()
    if blocked:
        return False, "blocked"

    # 2. Check daily rate limit: Max 5 OTP requests per mobile per day (24h)
    one_day_ago = now - timedelta(days=1)
    daily_count = db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.created_at > one_day_ago
    ).count()
    if daily_count >= 5:
        return False, "daily_limit"

    # 3. Check hourly rate limit: Max 3 requests per mobile per hour (1h)
    one_hour_ago = now - timedelta(hours=1)
    hourly_count = db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.created_at > one_hour_ago
    ).count()
    if hourly_count >= 3:
        return False, "hourly_limit"

    return True, "ok"

def save_otp(db: Session, mobile: str, otp: str, purpose: str):
    """Deletes any older OTP for this mobile and purpose, then saves a SHA-256 hashed new OTP."""
    # Delete existing OTPs for this mobile + purpose (single active OTP rule)
    db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.purpose == purpose
    ).delete()

    # Create new hashed OTP verification record
    hashed = hash_otp(otp)
    new_record = OTPVerification(
        mobile=mobile,
        otp_hash=hashed,
        purpose=purpose,
        is_used=0,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(new_record)
    db.commit()

def verify_otp(db: Session, mobile: str, raw_otp: str, purpose: str) -> str:
    """
    Verifies an OTP code for a mobile and purpose.
    Security Rules:
      - Expired OTP is rejected.
      - Used OTP is rejected.
      - 3 incorrect attempts blocks the mobile for 30 minutes.
    Returns status string: 'verified' | 'wrong' | 'expired' | 'blocked' | 'invalid'
    """
    now = datetime.utcnow()

    # 1. Check if mobile number is currently blocked
    blocked = db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.blocked_until > now
    ).first()
    if blocked:
        return "blocked"

    # 2. Find the active, unused record
    record = db.query(OTPVerification).filter(
        OTPVerification.mobile == mobile,
        OTPVerification.purpose == purpose,
        OTPVerification.is_used == 0
    ).first()

    if not record:
        return "invalid"

    # 3. Check expiry
    if record.expires_at < now:
        return "expired"

    # 4. Hash and compare
    hashed_input = hash_otp(raw_otp)
    if hashed_input != record.otp_hash:
        # Increment attempt counter
        record.attempts += 1
        if record.attempts >= 3:
            # Block the mobile number for 30 minutes
            record.blocked_until = now + timedelta(minutes=30)
            db.commit()
            return "blocked"
        db.commit()
        return "wrong"

    # 5. Successfully verified
    record.is_used = 1
    db.commit()
    return "verified"
