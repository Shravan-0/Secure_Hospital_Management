import sqlite3, tempfile, os
from pathlib import Path
import security.doctor_access as guard

fd, path = tempfile.mkstemp(suffix=".db")
os.close(fd)

def test_connect():
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

guard.connect = test_connect
guard.log_action = lambda *args, **kwargs: None

con = test_connect()
con.executescript("""
CREATE TABLE doctors(id INTEGER PRIMARY KEY, user_id INTEGER);
CREATE TABLE appointments(patient_id INTEGER, doctor_id INTEGER);
CREATE TABLE security_alerts(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL,
 alert_type TEXT NOT NULL,
 details TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 status TEXT DEFAULT 'Open',
 resolved_by TEXT,
 resolved_at TEXT
);
CREATE TABLE audit_logs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER, username TEXT, action TEXT, details TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO doctors VALUES(1, 2);
INSERT INTO doctors VALUES(2, 4);
INSERT INTO appointments VALUES(100, 1);
INSERT INTO appointments VALUES(200, 2);
""")
con.commit()
con.close()

doctor1 = {"id": 2, "username": "doctor1", "role": "Doctor"}
doctor2 = {"id": 4, "username": "doctor2", "role": "Doctor"}

# Doctor 1 can access their own assigned patient.
guard.require_assigned_patient(doctor1, 100, "test")
print("PASS: Assigned patient access allowed")

# Doctor 1 attempting Doctor 2's patient is blocked on attempts 1 and 2.
for expected in (1, 2):
    try:
        guard.require_assigned_patient(doctor1, 200, "test")
        raise AssertionError("Unauthorized access was allowed")
    except PermissionError as e:
        assert f"Warning {expected} of 3" in str(e), str(e)
        print(f"PASS: Warning {expected} displayed; attempt blocked")

# Third attempt triggers the 24-hour lock and admin alert.
try:
    guard.require_assigned_patient(doctor1, 200, "test")
    raise AssertionError("Third attempt was not blocked")
except PermissionError as e:
    assert "locked for 24 hours" in str(e)
    print("PASS: Third attempt triggers 24-hour lock")

con = test_connect()
control = con.execute(
    "SELECT violation_count, locked_until FROM doctor_access_controls WHERE user_id=2"
).fetchone()
alert = con.execute(
    "SELECT alert_type FROM security_alerts WHERE username='doctor1'"
).fetchone()
assert control["violation_count"] == 3 and control["locked_until"]
assert alert and alert["alert_type"] == "DOCTOR_ACCESS_LOCKED"
con.close()
print("PASS: Lock stored and Admin alert created")

# Doctor 2 remains unaffected.
guard.require_assigned_patient(doctor2, 200, "test")
print("PASS: Other doctor's account remains unaffected")

# Temporary test database retained; no deletion.
print("\nALL ISOLATED THREE-STRIKE TESTS PASSED")


