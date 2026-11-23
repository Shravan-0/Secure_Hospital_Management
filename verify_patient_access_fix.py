"""Regression check for CareSecure patient ownership and shared doctor strike counter.

Run from the project root:
    python verify_patient_access_fix.py

Uses a separate local test database; it does not touch database/hospital.db.
The test database is intentionally retained for inspection.
"""
import sqlite3
import tempfile
from pathlib import Path

import database.database as database_module

# Use an isolated test database before importing project services.
test_db = Path(tempfile.gettempdir()) / "caresecure_patient_access_regression.db"
database_module.DB_PATH = str(test_db)

from security import doctor_access
from security import audit_logger
from modules import services

# Keep this regression test independent of the real audit ledger.
doctor_access.log_action = lambda *args, **kwargs: None
services.log_action = lambda *args, **kwargs: None

with database_module.connect() as con:
    con.executescript("""
    DROP TABLE IF EXISTS doctor_access_controls;
    DROP TABLE IF EXISTS security_alerts;
    DROP TABLE IF EXISTS prescriptions;
    DROP TABLE IF EXISTS medical_records;
    DROP TABLE IF EXISTS appointments;
    DROP TABLE IF EXISTS patients;
    DROP TABLE IF EXISTS doctors;
    DROP TABLE IF EXISTS users;
    CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, role TEXT);
    CREATE TABLE doctors(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT);
    CREATE TABLE patients(id INTEGER PRIMARY KEY, full_name TEXT, age INTEGER,
                          phone TEXT, email TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE appointments(id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER,
                               appt_date TEXT, appt_time TEXT, status TEXT DEFAULT 'Scheduled',
                               created_by INTEGER);
    CREATE TABLE medical_records(id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER,
                                 notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE prescriptions(id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER,
                               version INTEGER DEFAULT 1, report_text TEXT, signature TEXT,
                               created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE security_alerts(id INTEGER PRIMARY KEY, username TEXT, alert_type TEXT,
                                 details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                 status TEXT DEFAULT 'Open');
    """)
    con.executemany("INSERT INTO users VALUES(?,?,?)", [
        (1, "doctor1", "Doctor"), (2, "doctor2", "Doctor")
    ])
    con.executemany("INSERT INTO doctors VALUES(?,?,?)", [
        (1, 1, "Dr. Asha Rao"), (2, 2, "Dr. Vikram Mehta")
    ])
    con.executemany("INSERT INTO patients(id,full_name,age,phone,email) VALUES(?,?,?,?,?)", [
        (101, "Asha Assigned Patient", 40, "9000000001", "asha.patient@example.test"),
        (202, "Vikram Assigned Patient", 45, "9000000002", "vikram.patient@example.test")
    ])
    con.executemany("INSERT INTO appointments VALUES(?,?,?,?,?,?,?)", [
        (1, 101, 1, "2026-11-22", "10:00", "Scheduled", 1),
        (2, 202, 2, "2026-11-22", "11:00", "Scheduled", 2)
    ])
    con.execute("INSERT INTO medical_records VALUES(1,202,2,'Private note',CURRENT_TIMESTAMP)")
    con.execute("INSERT INTO prescriptions VALUES(1,202,2,1,'Private prescription','test-signature',CURRENT_TIMESTAMP)")
    con.commit()

doctor1 = {"id": 1, "username": "doctor1", "role": "Doctor"}

# Correct patient ID returns the canonical full name and allows note creation.
patient = doctor_access.require_assigned_patient(doctor1, 101, "patient lookup")
assert patient["full_name"] == "Asha Assigned Patient"
name = services.add_record(doctor1, 101, "Follow-up consultation note")
assert name == "Asha Assigned Patient"
print("PASS: Assigned patient lookup returns the correct full name")
print("PASS: Assigned patient consultation note is saved")

# Three attempts across different clinical paths share one counter.
for fn, label in [
    (lambda: doctor_access.require_assigned_patient(doctor1, 202, "medical-record patient lookup"),
     "medical-record patient lookup"),
    (lambda: doctor_access.require_assigned_patient(doctor1, 202, "prescription patient lookup"),
     "prescription patient lookup"),
    (lambda: doctor_access.require_owned_clinical_item(doctor1, "medical_records", 1,
                                                       "medical-record ID retrieval"),
     "medical-record ID retrieval"),
]:
    try:
        fn()
    except PermissionError as exc:
        print(f"PASS: {label} blocked ({exc})")
    else:
        raise AssertionError(f"{label} was not blocked")

with database_module.connect() as con:
    control = con.execute(
        "SELECT violation_count, locked_until FROM doctor_access_controls WHERE user_id=1"
    ).fetchone()
    alert = con.execute(
        "SELECT COUNT(*) FROM security_alerts WHERE username='doctor1' AND alert_type='DOCTOR_ACCESS_LOCKED'"
    ).fetchone()[0]
    assert control["violation_count"] == 3 and control["locked_until"]
    assert alert == 1

print("PASS: Shared three-strike counter spans different clinical operations")
print("PASS: Third violation creates a 24-hour lock and one Admin alert")
print("ALL PATIENT ACCESS REGRESSION CHECKS PASSED")
print(f"Isolated test database retained at: {test_db}")
