import sys
import os

# Include the project root in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User
from services.auth_service import hash_password

def fix_admin_email():
    db = SessionLocal()
    try:
        phone = "7016998037"
        admin = db.query(User).filter(User.phone == phone).first()
        if admin:
            admin.email = "admin@agrismart.com"
            db.commit()
            print("[OK] Admin email successfully set to admin@agrismart.com!")
        else:
            print("[WARN] Admin user not found.")
    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_email()
