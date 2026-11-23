import sqlite3
from pathlib import Path
from config import DB_PATH

def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin','Doctor','Receptionist')),
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS doctors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS patients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120),
            phone TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS appointments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appt_date TEXT NOT NULL,
            appt_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            created_by INTEGER,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS medical_records(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );
        CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            from security.password_security import hash_password
            admin_hash = hash_password("Admin@123")
            doctor_hash = hash_password("Doctor@123")
            reception_hash = hash_password("Reception@123")
            con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                        ("admin", admin_hash, "Admin"))
            did = con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                              ("doctor1", doctor_hash, "Doctor")).lastrowid
            con.execute("INSERT INTO doctors(user_id,name,specialty) VALUES(?,?,?)",
                        (did, "Dr. Asha Rao", "General Medicine"))
            con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                        ("reception", reception_hash, "Receptionist"))
            con.execute("INSERT INTO patients(full_name,age,phone,created_by) VALUES(?,?,?,1)",
                        ("Sample Patient", 34, "9000000001"))
            con.execute("INSERT INTO appointments(patient_id,doctor_id,appt_date,appt_time,created_by) VALUES(1,1,date('now'), '10:30', 1)")
        # Forward-only schema migrations; existing patient and clinical rows are preserved.
        migrations = [
            "ALTER TABLE users ADD COLUMN otp_secret TEXT",
            "ALTER TABLE users ADD COLUMN otp_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN email TEXT",
            "ALTER TABLE users ADD COLUMN phone TEXT",
            "ALTER TABLE users ADD COLUMN otp_code_hash TEXT",
            "ALTER TABLE users ADD COLUMN otp_expires_at TEXT",
            "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN locked_until TEXT",
            "ALTER TABLE patients ADD COLUMN email TEXT",
            "ALTER TABLE patients ADD COLUMN phone TEXT",
        ]
        for statement in migrations:
            try: con.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower(): raise
        con.executescript("""
        CREATE TABLE IF NOT EXISTS security_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
            alert_type TEXT NOT NULL, details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Open', resolved_by TEXT, resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
            action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL,
            previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS prescriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL, version INTEGER NOT NULL DEFAULT 1,
            report_text TEXT NOT NULL, signature TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );
        """)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS doctor_access_controls(
            user_id INTEGER PRIMARY KEY,
            violation_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_violation_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_appointments_patient_doctor
            ON appointments(patient_id, doctor_id);
        CREATE INDEX IF NOT EXISTS idx_medical_records_doctor_patient
            ON medical_records(doctor_id, patient_id);
        CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor_patient
            ON prescriptions(doctor_id, patient_id);
        """)
        # Backfill the hash chain once for legacy audit events.
        ledger_count = con.execute("SELECT COUNT(*) FROM audit_ledger").fetchone()[0]
        if ledger_count == 0:
            from security.ledger import append_ledger
            legacy = con.execute("SELECT username,action,details,created_at FROM audit_logs ORDER BY id").fetchall()
            for item in legacy:
                append_ledger(con,item["username"],item["action"],item["details"],item["created_at"])
        # Optional local staff contacts are maintained in config/staff_contacts.json.
        import json
        contacts_file = Path("config/staff_contacts.json")
        if contacts_file.exists():
            try:
                contacts = json.loads(contacts_file.read_text(encoding="utf-8"))
                for uname, details in contacts.items():
                    if isinstance(details, dict):
                        con.execute("UPDATE users SET email=?, phone=? WHERE username=?",
                                    ((details.get("email") or None), (details.get("phone") or None), uname))
            except (OSError, ValueError, TypeError):
                pass
        con.commit()
