from datetime import datetime, timedelta
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


def _record_violation(user, operation, patient_id):
    """Persist one shared doctor-access strike and alert Admin on the third strike."""
    now = datetime.now()
    with connect() as con:
        _ensure_table(con)
        control = con.execute(
            "SELECT violation_count, locked_until FROM doctor_access_controls WHERE user_id=?",
            (user["id"],)
        ).fetchone()

        if control and control["locked_until"]:
            try:
                until = datetime.fromisoformat(control["locked_until"])
            except (TypeError, ValueError):
                until = None
            if until and now < until:
                raise PermissionError(
                    "Your account is temporarily locked for unauthorized patient access. "
                    "Please contact the administrator."
                )
            # Reset the strike count once the previous 24-hour lock has expired.
            con.execute(
                "UPDATE doctor_access_controls SET violation_count=0, locked_until=NULL WHERE user_id=?",
                (user["id"],)
            )
            count = 1
        else:
            count = (int(control["violation_count"]) if control else 0) + 1

        locked_until = (now + timedelta(hours=24)).isoformat(timespec="seconds") if count >= 3 else None
        con.execute("""
            INSERT INTO doctor_access_controls
                (user_id, violation_count, locked_until, last_violation_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                violation_count=excluded.violation_count,
                locked_until=excluded.locked_until,
                last_violation_at=excluded.last_violation_at
        """, (user["id"], count, locked_until, now.isoformat(timespec="seconds")))

        if count == 3:
            con.execute(
                "INSERT INTO security_alerts(username,alert_type,details) VALUES(?,?,?)",
                (user["username"], "DOCTOR_ACCESS_LOCKED",
                 f"Third unauthorized patient-access attempt ({operation}); account locked for 24 hours. Admin unlock required.")
            )
        con.commit()

    log_action(user, "UNAUTHORIZED_PATIENT_ACCESS",
               f"Blocked {operation}; warning {count} of 3; patient ID {patient_id}")
    if count >= 3:
        raise PermissionError(
            "Warning 3 of 3: Unauthorized access detected. "
            "Your account is locked for 24 hours and the administrator has been alerted."
        )
    raise PermissionError(
        f"Warning {count} of 3: You can access only patients assigned to you. "
        "This attempt was blocked and recorded."
    )


def require_assigned_patient(user, patient_id, operation="patient access"):
    """Return patient details only when an appointment assigns the patient to this doctor."""
    try:
        pid = int(patient_id)
    except (TypeError, ValueError):
        if user.get("role") == "Doctor":
            _record_violation(user, operation, repr(patient_id))
        raise ValueError("Enter a valid numeric patient ID.")

    if user.get("role") != "Doctor":
        with connect() as con:
            patient = con.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
        if not patient:
            raise ValueError("Patient ID was not found.")
        return patient

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
            except (TypeError, ValueError):
                until = None
            if until and now < until:
                raise PermissionError(
                    "Your account is temporarily locked for unauthorized patient access. "
                    "Please contact the administrator."
                )
            if until and now >= until:
                con.execute(
                    "UPDATE doctor_access_controls SET violation_count=0, locked_until=NULL WHERE user_id=?",
                    (user["id"],)
                )

        patient = con.execute("""
            SELECT p.* FROM patients p
            WHERE p.id=? AND EXISTS (
                SELECT 1 FROM appointments a
                WHERE a.patient_id=p.id AND a.doctor_id=?
            )
        """, (pid, doctor["id"])).fetchone()

    if patient:
        return patient
    _record_violation(user, operation, pid)


def require_owned_clinical_item(user, table, item_id, operation):
    """Count a strike if a doctor guesses another doctor's record/prescription ID."""
    if user.get("role") != "Doctor":
        raise PermissionError("This check is intended for doctor accounts.")
    if table not in ("medical_records", "prescriptions"):
        raise ValueError("Unsupported clinical item type.")
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        _record_violation(user, operation, repr(item_id))

    with connect() as con:
        doctor = con.execute(
            "SELECT id FROM doctors WHERE user_id=?", (user["id"],)
        ).fetchone()
        item = con.execute(
            f"SELECT patient_id, doctor_id FROM {table} WHERE id=?", (item_id,)
        ).fetchone()

    if not doctor:
        raise PermissionError("Doctor profile is not configured.")
    if not item:
        _record_violation(user, operation, f"unknown-{table}-ID-{item_id}")

    require_assigned_patient(user, item["patient_id"], operation)
    if int(item["doctor_id"]) != int(doctor["id"]):
        _record_violation(user, operation, item["patient_id"])
    return item
