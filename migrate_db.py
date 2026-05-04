"""
Run this ONCE to upgrade your existing hospital.db to the new schema.
Safely adds missing columns without deleting any data.

Usage:
    python migrate_db.py
"""
import sqlite3, os

# Find the database file
paths = [
    os.path.join(os.path.dirname(__file__), "instance", "hospital.db"),
    os.path.join(os.path.dirname(__file__), "hospital.db"),
]
DB_PATH = next((p for p in paths if os.path.exists(p)), None)

if not DB_PATH:
    print("No hospital.db found — run app.py first to create it, then run this script.")
    exit(0)

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

def column_exists(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def table_exists(table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

changes = []

# ── 1. Create doctor table if missing ─────────────────
if not table_exists("doctor"):
    cur.execute("""
        CREATE TABLE doctor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            specialisation VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            user_id INTEGER REFERENCES user_account(id),
            is_active BOOLEAN DEFAULT 1
        )
    """)
    changes.append("Created 'doctor' table")

# ── 2. Add doctor_id to patient if missing ────────────
if table_exists("patient") and not column_exists("patient", "doctor_id"):
    cur.execute("ALTER TABLE patient ADD COLUMN doctor_id INTEGER REFERENCES doctor(id)")
    changes.append("Added 'doctor_id' column to 'patient'")

# ── 3. Add report_image to lab_request if missing ─────
if table_exists("lab_request") and not column_exists("lab_request", "report_image"):
    cur.execute("ALTER TABLE lab_request ADD COLUMN report_image TEXT")
    changes.append("Added 'report_image' column to 'lab_request'")

# ── 4. Add updated_at to lab_request if missing ───────
if table_exists("lab_request") and not column_exists("lab_request", "updated_at"):
    cur.execute("ALTER TABLE lab_request ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    changes.append("Added 'updated_at' column to 'lab_request'")

# ── 5. Add is_active to user_account if missing ───────
if table_exists("user_account") and not column_exists("user_account", "is_active"):
    cur.execute("ALTER TABLE user_account ADD COLUMN is_active BOOLEAN DEFAULT 1")
    changes.append("Added 'is_active' to 'user_account'")

# ── 6. Create audit_log if missing ────────────────────
if not table_exists("audit_log"):
    cur.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(80),
            action VARCHAR(200),
            ip_address VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    changes.append("Created 'audit_log' table")

conn.commit()
conn.close()

if changes:
    print("Migration complete. Changes made:")
    for c in changes:
        print(f"  OK: {c}")
else:
    print("Database is already up to date. No changes needed.")
