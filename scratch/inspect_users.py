import sys
import os

# Include the project root in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import User

def inspect_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("=== REGISTERED USERS ===")
        if not users:
            print("No users found.")
        for u in users:
            print(f"ID: {u.id} | Name: {u.name} | Email: {u.email} | Phone: {u.phone} | Role: {u.role}")
    except Exception as e:
        print(f"Error inspecting users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_users()
