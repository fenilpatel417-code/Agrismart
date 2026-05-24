"""
migrate_db.py
─────────────
Adds new columns and tables to the existing agrismart.db
Run once: python migrate_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "agrismart.db")

def migrate():
    print("Running database migration...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create 'users' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100)  NOT NULL,
            phone      VARCHAR(20)   NOT NULL UNIQUE,
            password   VARCHAR(200)  NOT NULL,
            role       VARCHAR(20)   DEFAULT 'user',
            otp        VARCHAR(6)    NULL,
            otp_expiry DATETIME      NULL,
            created_at DATETIME      DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[OK] 'users' table ready.")

    # 2. Add 'mobile' and 'is_verified' columns to users if they don't exist
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]

    if "mobile" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN mobile VARCHAR(20) NULL")
        print("[OK] Added 'mobile' column to users.")
        # Migrate existing users' phone values to mobile
        cursor.execute("UPDATE users SET mobile = phone WHERE mobile IS NULL")
        print("[OK] Migrated existing 'phone' values to 'mobile'.")
        # Add UNIQUE index to mobile since alter table doesn't support adding UNIQUE directly in SQLite
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_mobile ON users(mobile)")
        print("[OK] Created unique index on users(mobile).")
    else:
        print("[OK] 'mobile' column already exists in users.")

    if "is_verified" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        print("[OK] Added 'is_verified' column to users.")
        # Set existing users as verified so they can log in immediately
        cursor.execute("UPDATE users SET is_verified = 1")
        print("[OK] Marked existing users as verified.")
    else:
        print("[OK] 'is_verified' column already exists in users.")

    # 3. Create 'otp_verification' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verification (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile        VARCHAR(20)   NOT NULL,
            otp_hash      VARCHAR(64)   NOT NULL,
            purpose       VARCHAR(20)   NOT NULL,
            attempts      INTEGER       DEFAULT 0,
            is_used       INTEGER       DEFAULT 0,
            blocked_until DATETIME      NULL,
            expires_at    DATETIME      NOT NULL,
            created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[OK] 'otp_verification' table ready.")

    # 4. Add 'user_id' column to scan_history if it doesn't exist
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
