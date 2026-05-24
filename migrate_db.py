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

    # 2. Add 'user_id' column to scan_history if it doesn't exist
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
