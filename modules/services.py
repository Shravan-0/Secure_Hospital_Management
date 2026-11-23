from database.database import connect
from security.access_control import require
from security.audit_logger import log_action
from security.validation import validate_patient, validate_date_time
from security.doctor_access import require_assigned_patient

def patients(user):
    require(user["role"], "patients.read" if user["role"] != "Doctor" else "patients.read_assigned")
    with connect() as con:
        if user["role"] == "Doctor":
            return con.execute("""SELECT DISTINCT p.* FROM patients p
                JOIN appointments a ON a.patient_id=p.id
                JOIN doctors d ON d.id=a.doctor_id WHERE d.user_id=? ORDER BY p.id DESC""",
                (user["id"],)).fetchall()
        return con.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()

def add_patient(user, name, age, phone, email=""):
    require(user["role"], "patients.write")
    name, age, phone = validate_patient(name, age, phone or "")
    email=(email or "").strip()
    if not phone and not email: raise ValueError("Enter at least an email address or mobile number.")
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise ValueError("Enter a valid email address.")
    with connect() as con:
        cur = con.execute("INSERT INTO patients(full_name,age,phone,created_by,email) VALUES(?,?,?,?,?)",
                          (name, age, phone, user["id"], email))
        pid = cur.lastrowid
        con.commit()
    log_action(user, "PATIENT_CREATED", f"Patient ID {pid}")
    return pid

def doctors():
    with connect() as con:
        return con.execute("SELECT * FROM doctors ORDER BY name").fetchall()

def appointments(user):
    require(user["role"], "appointments.read" if user["role"] != "Doctor" else "appointments.read_assigned")
    with connect() as con:
        sql = """SELECT a.id, a.patient_id, p.full_name, d.name AS doctor,
                        a.appt_date, a.appt_time, a.status
                 FROM appointments a
                 JOIN patients p ON p.id=a.patient_id
                 JOIN doctors d ON d.id=a.doctor_id"""
        if user["role"] == "Doctor":
            sql += " WHERE d.user_id=? ORDER BY a.appt_date,a.appt_time"
            return con.execute(sql, (user["id"],)).fetchall()
        return con.execute(sql + " ORDER BY a.appt_date,a.appt_time").fetchall()

def add_appointment(user, patient_id, doctor_id, date_text, time_text):
    require(user["role"], "appointments.write")
    validate_date_time(date_text, time_text)
    with connect() as con:
        cur = con.execute("""INSERT INTO appointments(patient_id,doctor_id,appt_date,appt_time,created_by)
                             VALUES(?,?,?,?,?)""",
                          (int(patient_id), int(doctor_id), date_text, time_text, user["id"]))
        aid = cur.lastrowid
        con.commit()
    log_action(user, "APPOINTMENT_CREATED", f"Appointment ID {aid}")
    return aid

def add_record(user, patient_id, notes):
    require(user["role"], "records.write_assigned" if user["role"] == "Doctor" else "records.write")
    if not isinstance(notes, str) or not notes.strip() or len(notes) > 1500:
        raise ValueError("Consultation notes must be 1–1500 characters.")
    patient_id = int(patient_id)

    # Check authorization before opening the write transaction.
    if user["role"] == "Doctor":
        patient = require_assigned_patient(user, patient_id, "consultation-note creation")
        with connect() as con:
            doctor = con.execute("SELECT id FROM doctors WHERE user_id=?", (user["id"],)).fetchone()
            if not doctor:
                raise PermissionError("Doctor profile is not configured.")
            doctor_id = int(doctor["id"])
            con.execute("INSERT INTO medical_records(patient_id,doctor_id,notes) VALUES(?,?,?)",
                        (patient_id, doctor_id, notes.strip()))
            con.commit()
        patient_name = patient["full_name"]
    else:
        with connect() as con:
            doctor = con.execute("SELECT id FROM doctors WHERE user_id=?", (user["id"],)).fetchone()
            doctor_id = int(doctor["id"]) if doctor else 1
            con.execute("INSERT INTO medical_records(patient_id,doctor_id,notes) VALUES(?,?,?)",
                        (patient_id, doctor_id, notes.strip()))
            con.commit()
        patient_name = None

    log_action(user, "MEDICAL_RECORD_CREATED",
               f"Patient ID {patient_id}; patient {patient_name or 'record'}; note content omitted")
    return patient_name


def records_for_doctor(user):
    require(user["role"], "records.read_assigned")
    with connect() as con:
        return con.execute("""SELECT m.id, m.patient_id, p.full_name, m.notes, m.created_at
          FROM medical_records m
          JOIN patients p ON p.id=m.patient_id
          JOIN doctors d ON d.id=m.doctor_id
          WHERE d.user_id=?
            AND EXISTS (
                SELECT 1 FROM appointments a
                WHERE a.patient_id=m.patient_id AND a.doctor_id=d.id
            )
          ORDER BY m.id DESC""", (user["id"],)).fetchall()


def get_medical_record_for_doctor(user, record_id):
    """Fetch a record only after checking patient assignment and record ownership."""
    from security.doctor_access import require_owned_clinical_item
    item = require_owned_clinical_item(
        user, "medical_records", record_id, "medical-record retrieval"
    )
    with connect() as con:
        return con.execute("""SELECT m.id, m.patient_id, p.full_name, m.doctor_id,
                                     m.notes, m.created_at
                              FROM medical_records m
                              JOIN patients p ON p.id=m.patient_id
                              WHERE m.id=? AND m.doctor_id=?""",
                           (int(record_id), int(item["doctor_id"]))).fetchone()


def create_user(admin, username, password, role, doctor_name="", specialty="General", email="", phone=""):
    require(admin["role"], "users.manage")
    from security.password_security import hash_password
    if len(username.strip()) < 3 or len(password) < 8:
        raise ValueError("Username must be at least 3 characters and password at least 8.")
    email=(email or "").strip(); phone=(phone or "").strip()
    if not email and not phone: raise ValueError("Enter at least an email address or mobile number.")
    if email and ("@" not in email or "." not in email.split("@")[-1]): raise ValueError("Enter a valid email address.")
    if role not in ("Doctor", "Receptionist", "Admin"):
        raise ValueError("Select a valid role.")
    with connect() as con:
        cur = con.execute("INSERT INTO users(username,password_hash,role,email,phone) VALUES(?,?,?,?,?)",
                          (username.strip(), hash_password(password), role, email or None, phone or None))
        uid = cur.lastrowid
        if role == "Doctor":
            if not doctor_name.strip():
                doctor_name = username.strip()
            con.execute("INSERT INTO doctors(user_id,name,specialty) VALUES(?,?,?)",
                        (uid, doctor_name.strip(), specialty.strip() or "General"))
        con.commit()
    log_action(admin, "USER_CREATED", f"Created {role} account: {username.strip()}")
    return uid

def audit_logs(user):
    require(user["role"], "logs.read")
    with connect() as con:
        return con.execute("SELECT created_at,username,action,details FROM audit_logs ORDER BY id DESC LIMIT 200").fetchall()

def dashboard_counts(user):
    require(user["role"], "patients.read" if user["role"] != "Doctor" else "patients.read_assigned")
    with connect() as con:
        d = con.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if user["role"] == "Doctor":
            doctor = con.execute("SELECT id FROM doctors WHERE user_id=?", (user["id"],)).fetchone()
            if not doctor:
                raise PermissionError("Doctor profile is not configured.")
            p = con.execute("SELECT COUNT(DISTINCT patient_id) FROM appointments WHERE doctor_id=?",
                            (doctor["id"],)).fetchone()[0]
            a = con.execute("SELECT COUNT(*) FROM appointments WHERE doctor_id=?",
                            (doctor["id"],)).fetchone()[0]
        else:
            p = con.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
            a = con.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    return p, a, d
