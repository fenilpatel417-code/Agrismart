"""
migrate_db.py
─────────────
Removes the OTP verification system and upgrades the user schema 
to support optional phone numbers and unique email addresses.
Run once: python migrate_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "agrismart.db")

def migrate():
    print("Running database migration...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current columns in users table
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]

    if "email" not in user_columns:
        print("[MIGRATION] Email column missing. Upgrading 'users' table schema...")
        
        # 1. Rename existing users table to users_old
        cursor.execute("ALTER TABLE users RENAME TO users_old")
        
        # 2. Create new users table with nullable phone and unique email
        cursor.execute("""
            CREATE TABLE users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       VARCHAR(100)  NOT NULL,
                email      VARCHAR(100)  NULL UNIQUE,
                phone      VARCHAR(20)   NULL UNIQUE,
                password   VARCHAR(200)  NOT NULL,
                role       VARCHAR(20)   DEFAULT 'user',
                created_at DATETIME      DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Copy existing user data from users_old to users
        cursor.execute("""
            INSERT INTO users (id, name, phone, password, role, created_at)
            SELECT id, name, phone, password, role, created_at FROM users_old
        """)
        print("[OK] Copied existing user records to the new schema.")
        
        # 4. Drop users_old
        cursor.execute("DROP TABLE users_old")
        print("[OK] Rebuilt 'users' table with optional phone and unique email columns.")
    else:
        print("[OK] 'users' table already has 'email' column.")

    # 5. Drop otp_verification table if it exists
    cursor.execute("DROP TABLE IF EXISTS otp_verification")
    print("[OK] Dropped 'otp_verification' table.")

    # 6. Ensure scan_history table exists and user_id is referenced
    cursor.execute("PRAGMA table_info(scan_history)")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE scan_history ADD COLUMN user_id INTEGER REFERENCES users(id)")
        print("[OK] Added 'user_id' column to scan_history.")
    else:
        print("[OK] 'user_id' column already exists in scan_history.")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
