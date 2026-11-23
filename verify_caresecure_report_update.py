from pathlib import Path
import ast
from io import BytesIO

for filename in ["main.py", "security/delivery.py", "security/report_pdf.py"]:
    ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
    print("SYNTAX OK:", filename)

from security.report_pdf import create_patient_report_pdf
from pypdf import PdfReader

for doctor, doctor_id in [("Dr. Asha Rao", 1), ("Dr. Vikram Mehta", 2)]:
    pdf = create_patient_report_pdf(
        patient_name="Karthik",
        patient_id=60,
        doctor_name=doctor,
        doctor_id=doctor_id,
        prescription="Suspected Iron-Deficiency Anemia (pending blood test confirmation).",
        signature="a" * 128,
    )
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) == 1, f"{doctor}: PDF has {len(reader.pages)} pages"
    page_text = reader.pages[0].extract_text()
    assert doctor in page_text
    assert "Karthik" in page_text
    assert "Ed25519" in page_text
    assert "SHA-256" in page_text
    assert len(pdf) > 1000
    print("ONE-PAGE PDF TEST PASSED:", doctor, "| bytes:", len(pdf))

delivery = Path("security/delivery.py").read_text(encoding="utf-8")
report_fn = delivery.split("def send_patient_report", 1)[1]
assert "send_sms(" not in report_fn
assert "_smtp_send(" in report_fn
assert "if not email:" in report_fn
print("EMAIL-ONLY REPORT DELIVERY TEST PASSED")

source = Path("main.py").read_text(encoding="utf-8")
assert 'SELECT id,name FROM doctors WHERE user_id=?' in source
assert "doctor={doc['name']}" in source
assert "create_patient_report_pdf" in source
print("DOCTOR NAME AND PDF INTEGRATION CHECK PASSED")

print("\nALL AUTOMATED CHECKS PASSED.")
