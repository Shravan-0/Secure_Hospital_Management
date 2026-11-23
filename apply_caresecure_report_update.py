from pathlib import Path
from datetime import datetime
import shutil, re, ast

root = Path.cwd()
main = root / "main.py"
delivery = root / "security" / "delivery.py"
pdf_file = root / "security" / "report_pdf.py"

if not main.exists() or not delivery.exists():
    raise SystemExit("ERROR: Run this from the CareSecure project folder.")

# Backup before making any changes.
backup = root / ("CareSecure_report_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
backup.mkdir()
shutil.copy2(main, backup / "main.py")
shutil.copy2(delivery, backup / "delivery.py")
if pdf_file.exists():
    shutil.copy2(pdf_file, backup / "report_pdf.py")

s = main.read_text(encoding="utf-8-sig")
d = delivery.read_text(encoding="utf-8-sig")

# Update doctor lookup to fetch professional name.
old_query = 'doc=con.execute("SELECT id FROM doctors WHERE user_id=?",(self.user["id"],)).fetchone()'
new_query = 'doc=con.execute("SELECT id,name FROM doctors WHERE user_id=?",(self.user["id"],)).fetchone()'

if old_query in s:
    s = s.replace(old_query, new_query, 1)
elif new_query not in s:
    raise SystemExit("STOP: Doctor lookup not found. No source files changed.")

# Sign the report using the doctor's real name, not their username.
old_name = "doctor={self.user['username']}"
new_name = "doctor={doc['name']}"
if old_name in s:
    s = s.replace(old_name, new_name, 1)
elif new_name not in s:
    raise SystemExit("STOP: Signed report doctor field not found. No source files changed.")

# Replace the existing plain-text PDF and email/SMS delivery section.
start_marker = "                    from security.delivery import send_patient_report"
end_marker = '                    messagebox.showinfo("Delivery submitted","Report sent to configured email/SMS channels.")'

start = s.find(start_marker)
end = s.find(end_marker, start)

if start < 0 or end < 0:
    raise SystemExit("STOP: Existing report-delivery block not found. No source files changed.")

end += len(end_marker)

new_block = '''                    from security.report_pdf import create_patient_report_pdf
                    from security.delivery import send_patient_report

                    if not patient["email"]:
                        raise ValueError("Patient email is missing. Add an email address to this patient's record first.")

                    pdf_bytes = create_patient_report_pdf(
                        patient_name=patient["full_name"],
                        patient_id=pid,
                        doctor_name=doc["name"],
                        doctor_id=doc["id"],
                        prescription=text,
                        signature=sig,
                    )

                    send_patient_report(patient["email"], None, payload, sig, pdf_bytes)
                    log_action(self.user,"PRESCRIPTION_DELIVERED",f"Signed PDF report emailed for patient ID {pid}")
                    messagebox.showinfo("Email submitted","The signed PDF report was submitted to the patient's registered email. SMS was not used.")'''

s = s[:start] + new_block + s[end:]

# Replace only the patient-report function. Preserve SMTP and OTP email delivery.
pattern = r"def send_patient_report\(email, phone, report_text, signature, pdf_bytes\):.*?(?=\n(?:def |\Z))"
replacement = '''def send_patient_report(email, phone, report_text, signature, pdf_bytes):
    """Email the signed PDF. Phone is intentionally ignored; no SMS is sent."""
    if not email:
        raise ValueError("Patient email address is required for report delivery.")
    _smtp_send(
        email,
        "Your CareSecure digitally signed patient report",
        "Your digitally signed CareSecure patient report is attached as a PDF. "
        "Please keep this confidential medical document secure.",
        pdf_bytes,
        "CareSecure_Patient_Report.pdf",
    )
'''
d_new, count = re.subn(pattern, replacement, d, flags=re.S)
if count != 1:
    raise SystemExit("STOP: Could not safely replace exactly one patient-report delivery function.")

# New professional one-page report generator.
pdf_code = r'''"""Professional one-page CareSecure report with Ed25519 QR verification data."""
from io import BytesIO
import hashlib
import json
import qrcode

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)


def create_patient_report_pdf(patient_name, patient_id, doctor_name,
                              doctor_id, prescription, signature):
    signed_payload = (
        f"patient_id={patient_id}|patient={patient_name}|doctor_id={doctor_id}"
        f"|doctor={doctor_name}|prescription={prescription}"
    )
    fingerprint = hashlib.sha256(signed_payload.encode("utf-8")).hexdigest()

    qr_data = json.dumps({
        "application": "CareSecure",
        "algorithm": "Ed25519",
        "patient_id": int(patient_id),
        "doctor_id": int(doctor_id),
        "report_sha256": fingerprint,
        "signature_hex": signature,
    }, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=5,
        border=3,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#123047", back_color="white").convert("RGB")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    navy = colors.HexColor("#123047")
    teal = colors.HexColor("#087E8B")
    pale = colors.HexColor("#EFF6F8")
    muted = colors.HexColor("#536675")
    border = colors.HexColor("#D7E2E8")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CSBrand", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=21, leading=24,
        textColor=navy, alignment=0, spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="CSSub", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7.5, leading=10,
        textColor=muted
    ))
    styles.add(ParagraphStyle(
        name="CSSection", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=9.5, leading=12,
        textColor=teal, spaceBefore=5, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="CSBody", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=navy
    ))
    styles.add(ParagraphStyle(
        name="CSSmall", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=6.5, leading=8,
        textColor=muted, wordWrap="CJK"
    ))
    styles.add(ParagraphStyle(
        name="CSValue", parent=styles["BodyText"],
        fontName="Helvetica-Bold", fontSize=9.5, leading=12,
        textColor=navy
    ))

    safe_patient = str(patient_name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_doctor = str(doctor_name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_prescription = (str(prescription).replace("&", "&amp;")
                         .replace("<", "&lt;").replace(">", "&gt;")
                         .replace("\n", "<br/>"))

    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        rightMargin=17*mm, leftMargin=17*mm,
        topMargin=12*mm, bottomMargin=12*mm,
        title="CareSecure - Digitally Signed Patient Report",
        author="CareSecure Hospital Management System",
    )

    story = []

    logo = Table([[
        Paragraph("+", ParagraphStyle(
            "CSLogo", fontName="Helvetica-Bold",
            fontSize=25, textColor=colors.white, alignment=1
        )),
        [
            Paragraph("CareSecure", styles["CSBrand"]),
            Paragraph("SECURE HOSPITAL MANAGEMENT SYSTEM", styles["CSSub"]),
        ],
    ]], colWidths=[18*mm, 145*mm])
    logo.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), teal),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story += [logo, Spacer(1, 5*mm)]
    story.append(Paragraph("DIGITALLY SIGNED PATIENT REPORT", styles["CSSection"]))
    story.append(Paragraph(
        "Confidential clinical document generated by CareSecure.",
        styles["CSSub"]
    ))
    story.append(Spacer(1, 4*mm))

    details = Table([
        [Paragraph("PATIENT", styles["CSSmall"]),
         Paragraph("RESPONSIBLE DOCTOR", styles["CSSmall"])],
        [Paragraph(safe_patient, styles["CSValue"]),
         Paragraph(safe_doctor, styles["CSValue"])],
        [Paragraph(f"Patient ID: {patient_id}", styles["CSSmall"]),
         Paragraph(f"Doctor ID: {doctor_id}", styles["CSSmall"])],
    ], colWidths=[81.5*mm, 81.5*mm])
    details.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), pale),
        ("BOX", (0,0), (-1,-1), 0.7, border),
        ("INNERGRID", (0,0), (-1,-1), 0.4, border),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 9),
        ("RIGHTPADDING", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story += [details, Spacer(1, 4*mm)]
    story.append(Paragraph("PRESCRIPTION / CLINICAL NOTES", styles["CSSection"]))

    clinical = Table([[Paragraph(safe_prescription, styles["CSBody"])]],
                     colWidths=[163*mm])
    clinical.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FAFCFD")),
        ("BOX", (0,0), (-1,-1), 0.7, border),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story += [clinical, Spacer(1, 4*mm)]
    story.append(Paragraph("DIGITAL SIGNATURE & QR VERIFICATION", styles["CSSection"]))

    qr_flowable = Image(qr_buffer, width=30*mm, height=30*mm)
    sig_display = signature[:32] + "..." + signature[-16:] if len(signature) > 55 else signature
    verification_text = [
        Paragraph("<b>Signature algorithm:</b> Ed25519", styles["CSBody"]),
        Paragraph("<b>Signature reference:</b>", styles["CSBody"]),
        Paragraph(sig_display, styles["CSSmall"]),
        Spacer(1, 2*mm),
        Paragraph("<b>Report SHA-256 fingerprint:</b>", styles["CSBody"]),
        Paragraph(fingerprint, styles["CSSmall"]),
        Spacer(1, 2*mm),
        Paragraph(
            "Scan the QR code to read the report verification payload. "
            "Verify the Ed25519 signature using the CareSecure public key.",
            styles["CSSmall"]
        ),
    ]
    verify = Table([[qr_flowable, verification_text]],
                   colWidths=[37*mm, 126*mm])
    verify.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), pale),
        ("BOX", (0,0), (-1,-1), 0.7, border),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story += [verify, Spacer(1, 4*mm)]
    story.append(Paragraph(
        "CONFIDENTIAL MEDICAL INFORMATION. Intended only for the patient "
        "and authorised healthcare professionals. Store securely.",
        styles["CSSmall"]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "CareSecure | Digitally signed clinical record",
        ParagraphStyle("CSFooter", parent=styles["CSSmall"], alignment=2)
    ))

    doc.build(story)
    return output.getvalue()
'''

# Validate all edits before writing.
ast.parse(s, filename="main.py")
ast.parse(d_new, filename="security/delivery.py")
ast.parse(pdf_code, filename="security/report_pdf.py")

main.write_text(s, encoding="utf-8")
delivery.write_text(d_new, encoding="utf-8")
pdf_file.write_text(pdf_code, encoding="utf-8")

print("SOURCE UPDATE COMPLETE")
print("Backup:", backup)
print("Updated: main.py")
print("Updated: security/delivery.py")
print("Created: security/report_pdf.py")
