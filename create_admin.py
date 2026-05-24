"""
create_admin.py
───────────────
Run once to create the default admin account:
  python create_admin.py

Creates: admin@agrismart.com / Admin@123 (if not already exists)
"""

import sys
import os

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import engine, Base, SessionLocal
from database.models import User
from services.auth_service import hash_password

def create_admin():
    # Create all tables if they don't exist yet
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        phone = "7016998037"
        existing = db.query(User).filter(User.phone == phone).first()
        
        if existing:
            print(f"[OK] Admin already exists: {existing.phone} (role: {existing.role})")
            return
            
        admin = User(
            name     = "Admin",
            phone    = phone,
            password = hash_password("Admin@123"),
            role     = "admin",
        )
        db.add(admin)
        db.commit()
        print("[OK] Admin account created successfully!")
        print(f"   Phone   : {phone}")
        print(f"   Password: Admin@123")
        print(f"   Role    : admin")
        print()
        print("[!]  Please change the password after your first login.")

    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
