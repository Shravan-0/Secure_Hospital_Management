from pathlib import Path
from datetime import datetime
import shutil

root = Path(".")
targets = [
    Path("main.py"),
    Path("modules/services.py"),
    Path("authentication/auth.py"),
]
for p in targets:
    if not p.exists():
        raise SystemExit(f"STOP: Missing file: {p}")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = Path(f"CareSecure_doctor_lock_backup_{stamp}")
backup.mkdir()
for p in targets:
    dest = backup / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
print("Backup created:", backup)

module = r'''from datetime import datetime, timedelta
from database.database import connect
from security.audit_logger import log_action


def _ensure_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS doctor_access_controls (
            user_id INTEGER PRIMARY KEY,
            violation_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_violation_at TEXT
        )
    """)


def require_assigned_patient(user, patient_id, operation):
    """Block unauthorized doctor access and apply a three-strike, 24-hour lock."""
    if user.get("role") != "Doctor":
        return

    now = datetime.now()
    with connect() as con:
        _ensure_table(con)

        doctor = con.execute(
            "SELECT id FROM doctors WHERE user_id=?", (user["id"],)
        ).fetchone()
        if not doctor:
            raise PermissionError("Doctor profile is not configured.")

        control = con.execute(
            "SELECT violation_count, locked_until FROM doctor_access_controls WHERE user_id=?",
            (user["id"],)
        ).fetchone()

        if control and control["locked_until"]:
            try:
                until = datetime.fromisoformat(control["locked_until"])
                if now < until:
                    raise PermissionError(
                        "Your account is temporarily locked for unauthorized patient access. "
                        "Please contact the administrator."
                    )
            except ValueError:
                pass

        assigned = con.execute(
            "SELECT 1 FROM appointments WHERE patient_id=? AND doctor_id=?",
            (int(patient_id), doctor["id"])
        ).fetchone()

        if assigned:
            return

        count = int(control["violation_count"]) if control else 0
        count += 1
        locked_until = None
        if count >= 3:
            locked_until = (now + timedelta(hours=24)).isoformat(timespec="seconds")

        con.execute("""
            INSERT INTO doctor_access_controls
                (user_id, violation_count, locked_until, last_violation_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                violation_count=excluded.violation_count,
                locked_until=excluded.locked_until,
                last_violation_at=excluded.last_violation_at
        """, (user["id"], count, locked_until, now.isoformat(timespec="seconds")))

        if count >= 3:
            con.execute(
                "INSERT INTO security_alerts(username,alert_type,details) VALUES(?,?,?)",
                (user["username"], "DOCTOR_ACCESS_LOCKED",
                 f"Third unauthorized patient-access attempt ({operation}); account locked for 24 hours. Admin unlock required.")
            )
        con.commit()

    log_action(
        user,
        "UNAUTHORIZED_PATIENT_ACCESS",
        f"Blocked {operation}; warning {count} of 3; patient ID {int(patient_id)}"
    )

    if count >= 3:
        raise PermissionError(
            "Warning 3 of 3: Unauthorized access detected. "
            "Your account is locked for 24 hours and the administrator has been alerted."
        )
    raise PermissionError(
        f"Warning {count} of 3: You can access only patients assigned to you. "
        "This attempt was blocked and recorded."
    )
'''
Path("security/doctor_access.py").write_text(module, encoding="utf-8")
print("Created security/doctor_access.py")

# Protect consultation-note creation at the service layer.
p = Path("modules/services.py")
s = p.read_text(encoding="utf-8")
if "from security.doctor_access import require_assigned_patient" not in s:
    s = s.replace(
        "from security.validation import validate_patient, validate_date_time",
        "from security.validation import validate_patient, validate_date_time\n"
        "from security.doctor_access import require_assigned_patient"
    )
old = '''            assigned = con.execute("SELECT 1 FROM appointments WHERE patient_id=? AND doctor_id=?",
                                   (int(patient_id), doctor["id"])).fetchone()
            if not assigned:
                raise PermissionError("You can only add notes for patients assigned to you.")
            doctor_id = doctor["id"]'''
new = '''            require_assigned_patient(user, patient_id, "consultation-note creation")
            doctor_id = doctor["id"]'''
if old not in s:
    raise SystemExit("STOP: Could not locate the exact add_record assignment check. No further files changed.")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("Updated modules/services.py")

# Protect prescription creation and make Admin unlock the correct lock type.
p = Path("main.py")
s = p.read_text(encoding="utf-8")
old = '''                assigned=con.execute("SELECT 1 FROM appointments WHERE patient_id=? AND doctor_id=?",(pid,doc["id"])).fetchone()
                if not assigned: raise PermissionError("You can prescribe only for your assigned patients.")'''
new = '''                from security.doctor_access import require_assigned_patient
                require_assigned_patient(self.user, pid, "prescription creation")'''
if old not in s:
    raise SystemExit("STOP: Could not locate the exact prescription assignment check.")
s = s.replace(old, new, 1)

# Make the Admin alert handler distinguish doctor-access locks from password locks.
old = '''            if action=="unlock":
                con.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE username=?",(username,))
                event="ACCOUNT_UNLOCKED"'''
new = '''            if action=="unlock":
                alert = con.execute("SELECT alert_type FROM security_alerts WHERE id=?", (alert_id,)).fetchone()
                if self.user.get("role") != "Admin":
                    raise PermissionError("Only an administrator can unlock accounts.")
                if alert and alert["alert_type"] == "DOCTOR_ACCESS_LOCKED":
                    account = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                    if account:
                        con.execute("""
                            UPDATE doctor_access_controls
                            SET violation_count=0, locked_until=NULL
                            WHERE user_id=?
                        """, (account["id"],))
                    event="DOCTOR_ACCESS_UNLOCKED"
                else:
                    con.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE username=?",(username,))
                    event="ACCOUNT_UNLOCKED"'''
if old not in s:
    raise SystemExit("STOP: Could not locate the exact Admin unlock handler.")
s = s.replace(old, new, 1)

# Update Admin page description to include both lockout types.
s = s.replace(
    'self.heading("Security alerts","Accounts locked after five failed password attempts")',
    'self.heading("Security alerts","Password lockouts and three-strike doctor access lockouts")',
    1
)
p.write_text(s, encoding="utf-8")
print("Updated main.py")

# Add the separate doctor lock check to the password-login stage.
p = Path("authentication/auth.py")
s = p.read_text(encoding="utf-8")
old = '''        user=dict(row); attempts=int(row["failed_attempts"] or 0)
        if row["locked_until"]:'''
new = '''        user=dict(row); attempts=int(row["failed_attempts"] or 0)
        if user.get("role") == "Doctor":
            con.execute("""
                CREATE TABLE IF NOT EXISTS doctor_access_controls (
                    user_id INTEGER PRIMARY KEY,
                    violation_count INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    last_violation_at TEXT
                )
            """)
            control = con.execute(
                "SELECT locked_until FROM doctor_access_controls WHERE user_id=?",
                (user["id"],)
            ).fetchone()
            if control and control["locked_until"]:
                try:
                    doctor_until = datetime.fromisoformat(control["locked_until"])
                    if datetime.now() < doctor_until:
                        return ("locked", None, doctor_until)
                except ValueError:
                    pass
        if row["locked_until"]:'''
if old not in s:
    raise SystemExit("STOP: Could not locate the login-stage insertion point.")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("Updated authentication/auth.py")
print("\nPATCH APPLIED. Backup:", backup)
