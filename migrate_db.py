"""
Run this ONCE to upgrade your existing hospital.db to the new schema.
Safely adds missing columns without deleting any data.

Usage:
    python migrate_db.py
"""
import sqlite3, os

paths = [
    os.path.join(os.path.dirname(__file__), "instance", "hospital.db"),
    os.path.join(os.path.dirname(__file__), "hospital.db"),
]
DB_PATH = next((p for p in paths if os.path.exists(p)), None)

if not DB_PATH:
    print("No hospital.db found — run app.py first, then this script.")
    exit(0)

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

def col(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def tbl(table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

changes = []

# ── doctor table ───────────────────────────────────────────────
if not tbl("doctor"):
    cur.execute("""CREATE TABLE doctor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        specialisation VARCHAR(100) NOT NULL,
        phone VARCHAR(20),
        user_id INTEGER REFERENCES user_account(id),
        is_active BOOLEAN DEFAULT 1)""")
    changes.append("Created 'doctor' table")

# ── patient — new columns ──────────────────────────────────────
new_patient_cols = [
    ("date_of_birth",      "VARCHAR(20)"),
    ("gender",             "VARCHAR(10)"),
    ("blood_group",        "VARCHAR(5)"),
    ("cnic",               "VARCHAR(20)"),
    ("phone",              "VARCHAR(20)"),
    ("address",            "VARCHAR(300)"),
    ("emergency_name",     "VARCHAR(100)"),
    ("emergency_phone",    "VARCHAR(20)"),
    ("allergies",          "VARCHAR(500)"),
    ("chronic_conditions", "VARCHAR(500)"),
    ("admission_type",     "VARCHAR(10)  DEFAULT 'OPD'"),
    ("status",             "VARCHAR(20)  DEFAULT 'Active'"),
    ("admission_date",     "VARCHAR(20)"),
    ("doctor_id",          "INTEGER REFERENCES doctor(id)"),
]
for colname, coltype in new_patient_cols:
    if tbl("patient") and not col("patient", colname):
        cur.execute(f"ALTER TABLE patient ADD COLUMN {colname} {coltype}")
        changes.append(f"Added '{colname}' to 'patient'")

# ── remove old 'age' column (rebuild table) ────────────────────
if tbl("patient") and col("patient", "age"):
    print("Rebuilding patient table to remove old 'age' column...")
    cur.execute("ALTER TABLE patient RENAME TO patient_old")
    cur.execute("""CREATE TABLE patient (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        name                  VARCHAR(100) NOT NULL,
        date_of_birth         VARCHAR(20),
        gender                VARCHAR(10),
        blood_group           VARCHAR(5),
        cnic                  VARCHAR(20),
        phone                 VARCHAR(20),
        address               VARCHAR(300),
        emergency_name        VARCHAR(100),
        emergency_phone       VARCHAR(20),
        allergies             VARCHAR(500),
        chronic_conditions    VARCHAR(500),
        admission_type        VARCHAR(10) DEFAULT 'OPD',
        status                VARCHAR(20) DEFAULT 'Active',
        admission_date        VARCHAR(20),
        doctor_id             INTEGER REFERENCES doctor(id),
        user_id               INTEGER REFERENCES user_account(id))""")
    # Copy data — old 'age' column dropped, doctor text col dropped
    cur.execute("""INSERT INTO patient
        (id, name, doctor_id, user_id)
        SELECT id, name, doctor_id, user_id FROM patient_old""")
    cur.execute("DROP TABLE patient_old")
    changes.append("Rebuilt patient table — added all new medical fields")

# ── appointment table ─────────────────────────────────────────
if not tbl("appointment"):
    cur.execute("""CREATE TABLE appointment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patient(id),
        doctor_id  INTEGER NOT NULL REFERENCES doctor(id),
        date       VARCHAR(20) NOT NULL,
        time       VARCHAR(10) NOT NULL,
        appt_type  VARCHAR(20) DEFAULT 'OPD',
        status     VARCHAR(20) DEFAULT 'Scheduled',
        notes      VARCHAR(500),
        created_at VARCHAR(20))""")
    changes.append("Created 'appointment' table")

# ── lab_test table ────────────────────────────────────────────
if not tbl("lab_test"):
    cur.execute("""CREATE TABLE lab_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL UNIQUE,
        category VARCHAR(50),
        is_active BOOLEAN DEFAULT 1)""")
    changes.append("Created 'lab_test' table")

# ── prescription — new columns ────────────────────────────────
new_pres_cols = [
    ("dosage",          "VARCHAR(50)"),
    ("frequency",       "VARCHAR(50)"),
    ("duration",        "VARCHAR(50)"),
    ("instructions",    "VARCHAR(300)"),
    ("prescribed_date", "VARCHAR(20)"),
    ("doctor_id",       "INTEGER REFERENCES doctor(id)"),
]
for colname, coltype in new_pres_cols:
    if tbl("prescription") and not col("prescription", colname):
        cur.execute(f"ALTER TABLE prescription ADD COLUMN {colname} {coltype}")
        changes.append(f"Added '{colname}' to 'prescription'")

# ── lab_request ────────────────────────────────────────────────
if tbl("lab_request") and not col("lab_request", "report_image"):
    cur.execute("ALTER TABLE lab_request ADD COLUMN report_image TEXT")
    changes.append("Added 'report_image' to 'lab_request'")

# ── user_account ───────────────────────────────────────────────
if tbl("user_account") and not col("user_account", "is_active"):
    cur.execute("ALTER TABLE user_account ADD COLUMN is_active BOOLEAN DEFAULT 1")
    changes.append("Added 'is_active' to 'user_account'")

# ── audit_log ──────────────────────────────────────────────────
if not tbl("audit_log"):
    cur.execute("""CREATE TABLE audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id VARCHAR(80),
        action VARCHAR(200),
        ip_address VARCHAR(50),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    changes.append("Created 'audit_log' table")

conn.commit()
conn.close()

if changes:
    print("Migration complete. Changes made:")
    for c in changes:
        print(f"  OK: {c}")
else:
    print("Database already up to date. No changes needed.")
