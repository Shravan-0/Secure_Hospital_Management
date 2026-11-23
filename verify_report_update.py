from pathlib import Path
import ast, sqlite3, sys

files = [
    Path("main.py"),
    Path("security/delivery.py"),
    Path("security/report_pdf.py"),
]
for f in files:
    ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
    print("SYNTAX OK:", f)

from security.report_pdf import create_patient_report_pdf
from pypdf import PdfReader
from io import BytesIO

pdf = create_patient_report_pdf(
    patient_name="Karthik",
    patient_id=60,
    doctor_name="Dr. Vikram Mehta",
    doctor_id=2,
    prescription="Suspected Iron-Deficiency Anemia (pending blood test confirmation).",
    signature="a" * 128,
)
reader = PdfReader(BytesIO(pdf))
assert len(reader.pages) == 1, f"Expected one page, got {len(reader.pages)}"
text = reader.pages[0].extract_text()
assert "Dr. Vikram Mehta" in text
assert "Karthik" in text
assert "Ed25519" in text
assert "SHA-256" in text
print("PDF TEST PASSED: one page, doctor name, patient name, Ed25519 and SHA-256 present.")
print("PDF bytes:", len(pdf))

# Verify that delivery is explicitly email-only.
delivery = Path("security/delivery.py").read_text(encoding="utf-8")
assert "send_sms(" not in delivery
assert "def send_patient_report" in delivery
assert "if not email:" in delivery
print("EMAIL-ONLY DELIVERY CHECK PASSED: patient report code does not call SMS.")
