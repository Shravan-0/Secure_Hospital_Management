"""Add a larger, fictional CareSecure demo dataset.

Run from the project root:
    python seed_extended_demo_data.py

Safe to run more than once: existing demo patients, doctor account,
appointments and consultation notes are checked before insertion.
"""
from datetime import date, timedelta
import sqlite3
from pathlib import Path
from config import DB_PATH
from database.database import connect, initialize
from security.password_security import hash_password

PATIENTS = [('Aarav Menon', 28), ('Diya Iyer', 34), ('Kabir Shah', 41), ('Ananya Reddy', 25), ('Ishaan Gupta', 53), ('Saanvi Kulkarni', 31), ('Vihaan Patel', 47), ('Aditi Joshi', 22), ('Reyansh Verma', 39), ('Myra Nair', 56), ('Advait Rao', 44), ('Kiara Das', 19), ('Arjun Bhat', 62), ('Ira Choudhary', 37), ('Rohan Pillai', 29), ('Tara Kapoor', 48), ('Neil Fernandes', 33), ('Pooja Shetty', 51), ('Dev Malhotra', 26), ('Nisha Thomas', 43), ('Karthik Hegde', 35), ('Mira Banerjee', 58), ('Yash Agarwal', 24), ('Sara Khan', 40), ('Manav Sinha', 67), ('Lavanya Krishnan', 30), ('Dhruv Jain', 46), ('Ritika Bose', 27), ('Aditya Rao', 55), ('Shreya Nambiar', 32), ('Om Prakash', 60), ('Ishita Ghosh', 21), ('Rahul Chawla', 49), ('Tanvi Desai', 38), ('Siddharth Roy', 42), ('Megha Pillai', 23), ('Varun Bansal', 64), ('Ayesha Ali', 36), ('Nikhil Ramesh', 50), ('Rhea Dutta', 28), ('Samar Khanna', 45), ('Kavya Menon', 33), ('Harsh Venkatesh', 57), ('Manya Sethi', 20), ('Gautam Naidu', 52), ('Ishani Mukherjee', 29), ('Pranav Kulkarni', 61), ('Zoya Qureshi', 34), ('Suresh Babu', 70), ('Nandini Rao', 26)]

def ensure_user(con, username, password, role):
    row = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if row:
        return row["id"]
    return con.execute(
        "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,1)",
        (username, hash_password(password), role)
    ).lastrowid

def main():
    initialize()
    with connect() as con:
        admin_id = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()["id"]
        doctor1_user = con.execute("SELECT id FROM users WHERE username='doctor1'").fetchone()
        if not doctor1_user:
            raise RuntimeError("Default doctor1 account is missing.")
        doctor1_id = con.execute("SELECT id FROM doctors WHERE user_id=?", (doctor1_user["id"],)).fetchone()["id"]

        doctor2_user_id = ensure_user(con, "doctor2", "Doctor2@123", "Doctor")
        doctor2 = con.execute("SELECT id FROM doctors WHERE user_id=?", (doctor2_user_id,)).fetchone()
        if doctor2:
            doctor2_id = doctor2["id"]
        else:
            doctor2_id = con.execute(
                "INSERT INTO doctors(user_id,name,specialty) VALUES(?,?,?)",
                (doctor2_user_id, "Dr. Vikram Mehta", "Family Medicine")
            ).lastrowid

        # Add enough fictional patients to reach at least 50 in total.
        for index, (name, age) in enumerate(PATIENTS, start=1):
            phone = f"900001{index:04d}"
            exists = con.execute("SELECT id FROM patients WHERE phone=?", (phone,)).fetchone()
            if not exists:
                con.execute(
                    "INSERT INTO patients(full_name,age,phone,created_by) VALUES(?,?,?,?)",
                    (name, age, phone, admin_id)
                )

        patients = con.execute("SELECT id FROM patients ORDER BY id").fetchall()
        # Give every patient at least one appointment and one consultation note.
        base_date = date.today() + timedelta(days=1)
        note_templates = [
            "Routine consultation. Patient reports feeling generally well. Vital signs reviewed; follow-up advised as appropriate.",
            "Follow-up visit for a previously reported concern. Symptoms and general wellbeing reviewed. Continue routine monitoring.",
            "General health review completed. Lifestyle, hydration and rest discussed. Return for review if symptoms persist.",
            "Consultation completed. Relevant history reviewed and care instructions explained to the patient.",
            "Preventive health discussion completed. Patient advised on routine check-up and healthy daily habits."
        ]
        for index, patient in enumerate(patients):
            patient_id = patient["id"]
            doctor_id = doctor1_id if index % 2 == 0 else doctor2_id
            appt_day = (base_date + timedelta(days=index % 14)).isoformat()
            appt_time = f"{9 + (index % 8):02d}:{'00' if index % 2 == 0 else '30'}"
            appointment = con.execute(
                """SELECT id FROM appointments
                   WHERE patient_id=? AND doctor_id=? AND appt_date=? AND appt_time=?""",
                (patient_id, doctor_id, appt_day, appt_time)
            ).fetchone()
            if not appointment:
                con.execute(
                    """INSERT INTO appointments(patient_id,doctor_id,appt_date,appt_time,status,created_by)
                       VALUES(?,?,?,?,?,?)""",
                    (patient_id, doctor_id, appt_day, appt_time, "Scheduled", admin_id)
                )
            record = con.execute(
                "SELECT id FROM medical_records WHERE patient_id=? AND doctor_id=? LIMIT 1",
                (patient_id, doctor_id)
            ).fetchone()
            if not record:
                note = note_templates[index % len(note_templates)]
                con.execute(
                    "INSERT INTO medical_records(patient_id,doctor_id,notes) VALUES(?,?,?)",
                    (patient_id, doctor_id, note)
                )
        con.commit()

        total_patients = con.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        total_doctors = con.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        total_appointments = con.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        total_records = con.execute("SELECT COUNT(*) FROM medical_records").fetchone()[0]

    print("Extended fictional demo data is ready.")
    print(f"Patients: {total_patients}")
    print(f"Doctors: {total_doctors}")
    print(f"Appointments: {total_appointments}")
    print(f"Medical records / notes: {total_records}")
    print("\nDoctor 2 login: username=doctor2, password=Doctor2@123")
    print("Doctor 2 profile: Dr. Vikram Mehta (Family Medicine)")

if __name__ == "__main__":
    main()
