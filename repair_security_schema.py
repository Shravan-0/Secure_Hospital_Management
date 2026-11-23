"""Safely add missing CareSecure 2.0 security tables to the existing SQLite DB.
Does not delete or rewrite patients, appointments, medical records, or users.
Run from the folder containing main.py: python repair_security_schema.py
"""
from database.database import connect
from security.ledger import append_ledger, verify_ledger


def add_column(con, table, definition):
    name = definition.split()[0]
    existing = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if name not in existing:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
        print(f"Added {table}.{name}")


def main():
    with connect() as con:
        # Account security state
        add_column(con, "users", "otp_secret TEXT")
        add_column(con, "users", "otp_enabled INTEGER NOT NULL DEFAULT 0")
        add_column(con, "users", "failed_attempts INTEGER NOT NULL DEFAULT 0")
        add_column(con, "users", "locked_until TEXT")
        # Optional patient email for doctor-approved report delivery
        add_column(con, "patients", "email TEXT")

        con.executescript("""
        CREATE TABLE IF NOT EXISTS security_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Open',
            resolved_by TEXT,
            resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS prescriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            report_text TEXT NOT NULL,
            signature TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM audit_ledger").fetchone()[0]
        if count == 0:
            legacy = con.execute(
                "SELECT username, action, details, created_at FROM audit_logs ORDER BY id"
            ).fetchall()
            for item in legacy:
                append_ledger(con, item["username"], item["action"], item["details"], item["created_at"])
            print(f"Imported {len(legacy)} existing audit events into the hash chain.")
        con.commit()

    ok, detail = verify_ledger()
    print("Audit ledger:", "VERIFIED" if ok else f"TAMPERING DETECTED at entry {detail}")
    with connect() as con:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        print("Security tables present:", all(x in names for x in ("security_alerts", "audit_ledger", "prescriptions")))
        print("Preserved patients:", con.execute("SELECT COUNT(*) FROM patients").fetchone()[0])
        print("Preserved appointments:", con.execute("SELECT COUNT(*) FROM appointments").fetchone()[0])
        print("Preserved medical records:", con.execute("SELECT COUNT(*) FROM medical_records").fetchone()[0])


if __name__ == "__main__":
    main()
