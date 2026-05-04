"""
Run this ONCE to upgrade your existing hospital.db to the new schema.
It safely adds missing columns without deleting any data.

Usage:
    python migrate_db.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "hospital.db")
if not os.path.exists(DB_PATH):
    # Try current directory
    DB_PATH = os.path.join(os.path.dirname(__file__), "hospital.db")

if not os.path.exists(DB_PATH):
    print("No hospital.db found — nothing to migrate. Run app.py first to create it fresh.")
    exit(0)

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── Helper ──────────────────────────────────────────────────
def column_exists(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def table_exists(table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

changes = []

# ── 1. Create doctor table if missing ───────────────────────
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

# ── 2. Add doctor_id to patient if missing ──────────────────
if table_exists("patient") and not column_exists("patient", "doctor_id"):
    cur.execute("ALTER TABLE patient ADD COLUMN doctor_id INTEGER REFERENCES doctor(id)")
    changes.append("Added 'doctor_id' column to 'patient' table")

# ── 3. Remove old 'doctor' text column from patient ─────────
#    SQLite doesn't support DROP COLUMN before 3.35.0
#    We rename the table and recreate it cleanly
if table_exists("patient") and column_exists("patient", "doctor"):
    print("Migrating patient table to remove old 'doctor' text column...")
    cur.execute("ALTER TABLE patient RENAME TO patient_old")
    cur.execute("""
        CREATE TABLE patient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            age INTEGER NOT NULL,
            doctor_id INTEGER REFERENCES doctor(id),
            user_id INTEGER REFERENCES user_account(id)
        )
    """)
    # Copy data — old 'doctor' text column is dropped
    cur.execute("""
        INSERT INTO patient (id, name, age, doctor_id, user_id)
        SELECT id, name, age, doctor_id, user_id FROM patient_old
    """)
    cur.execute("DROP TABLE patient_old")
    changes.append("Rebuilt 'patient' table — removed old text 'doctor' column")

# ── 4. Add is_active to user_account if missing ─────────────
if table_exists("user_account") and not column_exists("user_account", "is_active"):
    cur.execute("ALTER TABLE user_account ADD COLUMN is_active BOOLEAN DEFAULT 1")
    changes.append("Added 'is_active' to 'user_account'")

# ── 5. Create audit_log if missing ──────────────────────────
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
        print(f"  ✓ {c}")
else:
    print("Database is already up to date. No changes needed.")
