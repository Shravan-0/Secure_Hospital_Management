import re

def validate_patient(name, age, phone):
    name = name.strip()
    if len(name) < 2 or len(name) > 80:
        raise ValueError("Patient name must be 2–80 characters.")
    if not age.isdigit() or not 0 <= int(age) <= 120:
        raise ValueError("Age must be a number between 0 and 120.")
    phone=(phone or "").strip()
    if phone and not re.fullmatch(r"[0-9+\- ]{7,15}", phone):
        raise ValueError("Enter a valid phone number (7–15 digits or +, spaces, hyphens).")
    return name, int(age), phone

def validate_date_time(date_text, time_text):
    from datetime import date, time
    try:
        date.fromisoformat(date_text)
        time.fromisoformat(time_text)
    except ValueError:
        raise ValueError("Use date YYYY-MM-DD and time HH:MM.")
