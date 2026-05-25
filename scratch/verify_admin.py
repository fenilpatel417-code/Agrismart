import sys
import os

# Include the project root in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User
from services.auth_service import verify_password, hash_password

def verify_and_fix_admin():
    db = SessionLocal()
    try:
        phone = "7016998037"
        admin = db.query(User).filter(User.phone == phone).first()
        if not admin:
            print("[WARN] Admin user not found. Creating a new admin user...")
            admin = User(
                name="Admin",
                phone=phone,
                password=hash_password("Admin@123"),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("[OK] Admin user created with password: Admin@123")
            return

        # Check if Admin@123 works
        if verify_password("Admin@123", admin.password):
            print("[OK] Admin password is correct: Admin@123 hashes successfully!")
        else:
            print("[WARN] Admin password mismatch in database. Resetting it to Admin@123...")
            admin.password = hash_password("Admin@123")
            db.commit()
            print("[OK] Admin password has been successfully reset to Admin@123!")

    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    verify_and_fix_admin()
