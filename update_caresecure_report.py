from pathlib import Path
from datetime import datetime
import shutil, re, sys, hashlib

ROOT = Path.cwd()
main = ROOT / "main.py"
delivery = ROOT / "security" / "delivery.py"
report_module = ROOT / "security" / "report_pdf.py"

if not main.exists() or not delivery.exists():
    raise SystemExit("ERROR: Run this from the CareSecure project folder containing main.py and security/delivery.py")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / ("CareSecure_backup_" + stamp)
backup.mkdir()
shutil.copy2(main, backup / "main.py")
shutil.copy2(delivery, backup / "delivery.py")
if report_module.exists():
    shutil.copy2(report_module, backup / "report_pdf.py")

s = main.read_text(encoding="utf-8")
d = delivery.read_text(encoding="utf-8")

# 1. Fetch the doctor's professional name as well as their ID.
old_doc = 'doc=con.execute("SELECT id FROM doctors WHERE user_id=?",(self.user["id"],)).fetchone()'
new_doc = 'doc=con.execute("SELECT id,name FROM doctors WHERE user_id=?",(self.user["id"],)).fetchone()'
if old_doc not in s:
    if new_doc not in s:
        raise SystemExit("STOP: Could not locate the expected doctor lookup in main.py. No source changes made.")
else:
    s = s.replace(old_doc, new_doc, 1)

# 2. Put the doctor's real name into the signed report content.
old_payload = 'payload=f"patient_id={pid}|patient={patient[\\'full_name\\']}|doctor_id={doc[\\'id\\']}|doctor={self.user[\\'username\\']}|prescription={text}"'
new_payload = 'payload=f"patient_id={pid}|patient={patient[\\'full_name\\']}|doctor_id={doc[\\'id\\']}|doctor={doc[\\'name\\']}|prescription={text}"'
if old_payload not in s:
    if "doctor={doc['name']}" not in s:
        raise SystemExit("STOP: Could not locate the expected signed-report payload. No source changes made.")
else:
    s = s.replace(old_payload, new_payload, 1)

# 3. Replace the old plain-text PDF creation and SMS-capable delivery.
start_marker = '                    from security.delivery import send_patient_report'
end_marker = '                    messagebox.showinfo("Delivery submitted","Report sent to configured email/SMS channels.")'
start = s.find(start_marker)
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("STOP: Could not locate the existing report-delivery block. No source changes made.")

end += len(end_marker)
replacement = '''                    from security.report_pdf import create_patient_report_pdf
                    from security.delivery import send_patient_report
                    pdf_bytes = create_patient_report_pdf(
                        patient_name=patient["full_name"],
                        patient_id=pid,
                        doctor_name=doc["name"],
                        doctor_id=doc["id"],
                        prescription=text,
                        signature=sig,
                    )
                    if not patient["email"]:
                        raise ValueError("This patient has no registered email address. Add the email address to the patient record first.")
                    send_patient_report(patient["email"], None, payload, sig, pdf_bytes)
                    log_action(self.user,"PRESCRIPTION_DELIVERED",f"Signed PDF report emailed for patient ID {pid}")
                    messagebox.showinfo("Email submitted","The signed PDF report was submitted to the patient's registered email address. No SMS was attempted.")'''
s = s[:start] + replacement + s[end:]

# 4. Make patient report delivery email-only. Phone numbers are deliberately ignored.
delivery_new = '''"""Email-only delivery for CareSecure OTPs and signed patient PDF reports."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def _smtp_send(to, subject, body, attachment=None, filename=None):
    host = os.getenv("CARESECURE_SMTP_HOST")
    user = os.getenv("CARESECURE_SMTP_USER")
    pwd = os.getenv("CARESECURE_SMTP_PASSWORD")
    sender = os.getenv("CARESECURE_FROM_EMAIL", user or "")
    port = int(os.getenv("CARESECURE_SMTP_PORT", "587"))

    if not all([host, user, pwd, sender]):
        raise RuntimeError("Email is not configured. Check CARESECURE_SMTP_* settings in .env.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)
    if attachment:
        msg.add_attachment(
            attachment,
            maintype="application",
            subtype="pdf",
            filename=filename or "CareSecure_Patient_Report.pdf",
        )

    # Explicit EHLO and localhost hostname for compatible Gmail STARTTLS negotiation.
    with smtplib.SMTP(host, port, local_hostname="localhost", timeout=25) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(user, pwd)
        server.send_message(msg)


def send_otp(channel, destination, code):
    body = f"Your CareSecure verification code is {code}. It expires in 5 minutes. Do not share it."
    if os.getenv("CARESECURE_DEMO_MODE", "1") == "1":
        print(f"\\n[CARESOURCE DEMO OTP] {channel.upper()} to {destination}: {code} (5 min)\\n")
        return
    if channel != "email":
        raise ValueError("CareSecure is configured for email OTP only.")
    _smtp_send(destination, "CareSecure login verification code", body)


def send_patient_report(email, phone, report_text, signature, pdf_bytes):
    # Phone is retained in the function signature for compatibility, but is never used.
    if not email:
        raise ValueError("Patient email address is required for PDF report delivery.")
    _smtp_send(
        email,
        "Your CareSecure digitally signed patient report",
        "Your digitally signed CareSecure patient report is attached as a PDF. "
        "Please keep it private and share it only with your healthcare provider.",
        pdf_bytes,
        "CareSecure_Patient_Report.pdf",
    )
'''
d = delivery_new

# 5. Create a professional, one-page A4 PDF with vector logo and QR verification payload.
pdf_code = r'''"""One-page CareSecure patient report PDF with Ed25519 QR verification payload."""
from io import BytesIO
import hashlib
import json
import qrcode

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether
)


def create_patient_report_pdf(patient_name, patient_id, doctor_name,
                              doctor_id, prescription, signature):
    # The signature is over the exact report payload created by the application.
    signed_payload = (
        f"patient_id={patient_id}|patient={patient_name}|doctor_id={doctor_id}"
        f"|doctor={doctor_name}|prescription={prescription}"
    )
    fingerprint = hashlib.sha256(signed_payload.encode("utf-8")).hexdigest()
    qr_payload = json.dumps({
        "application": "CareSecure",
        "algorithm": "Ed25519",
        "patient_id": int(patient_id),
        "doctor_id": int(doctor_id),
        "report_sha256": fingerprint,
        "signature_hex": signature,
    }, separators=(",", ":"))

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=5, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="#123047", back_color="white").convert("RGB")
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    buffer = BytesIO()
    navy = colors.HexColor("#123047")
    teal = colors.HexColor("#087E8B")
    pale = colors.HexColor("#EFF6F8")
    muted = colors.HexColor("#5B6B78")
    line = colors.HexColor("#D9E3E8")

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=13*mm, bottomMargin=13*mm,
        title="CareSecure - Digitally Signed Patient Report",
        author="CareSecure Hospital Management System",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Brand", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=23, textColor=navy, alignment=TA_LEFT, spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="SubBrand", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=11, textColor=muted
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=10, leading=13, textColor=teal, spaceBefore=7, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="BodyCare", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9, leading=13, textColor=navy
    ))
    styles.add(ParagraphStyle(
        name="SmallCare", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7, leading=9, textColor=muted
    ))
    styles.add(ParagraphStyle(
        name="ValueCare", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=9, leading=12, textColor=navy
    ))

    story = []
    logo = Table(
        [[Paragraph("✚", ParagraphStyle("LogoMark", fontName="Helvetica-Bold",
                                         fontSize=23, textColor=colors.white)),
          [Paragraph("CareSecure", styles["Brand"]),
           Paragraph("SECURE HOSPITAL MANAGEMENT  |  DIGITALLY SIGNED CLINICAL DOCUMENT", styles["SubBrand"])]]],
        colWidths=[17*mm, 145*mm]
    )
    logo.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), teal),
        ("BACKGROUND", (1,0), (1,0), colors.white),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story += [logo, Spacer(1, 7*mm)]
    story.append(Paragraph("DIGITALLY SIGNED PATIENT REPORT", styles["Section"]))
    story.append(Paragraph(
        "A clinical document generated and digitally signed within the CareSecure system.",
        styles["SubBrand"]
    ))
    story.append(Spacer(1, 4*mm))

    patient_rows = [
        [Paragraph("PATIENT", styles["SmallCare"]), Paragraph("REPORTING DOCTOR", styles["SmallCare"])],
        [Paragraph(str(patient_name), styles["ValueCare"]), Paragraph(str(doctor_name), styles["ValueCare"])],
        [Paragraph(f"Patient ID: {patient_id}", styles["SmallCare"]),
         Paragraph(f"Doctor ID: {doctor_id}", styles["SmallCare"])],
    ]
    patient_table = Table(patient_rows, colWidths=[81*mm, 81*mm])
    patient_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), pale),
        ("BOX", (0,0), (-1,-1), 0.6, line),
        ("INNERGRID", (0,0), (-1,-1), 0.4, line),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story += [patient_table, Spacer(1, 5*mm)]
    story.append(Paragraph("PRESCRIPTION / CLINICAL NOTES", styles["Section"]))
    safe_text = (str(prescription).replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\\n", "<br/>"))
    clinical = Table([[Paragraph(safe_text, styles["BodyCare"])]], colWidths=[162*mm])
    clinical.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FAFCFD")),
        ("BOX", (0,0), (-1,-1), 0.7, line),
        ("LEFTPADDING", (0,0), (-1,-1), 11),
        ("RIGHTPADDING", (0,0), (-1,-1), 11),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    story += [clinical, Spacer(1, 5*mm), Paragraph("DIGITAL SIGNATURE & VERIFICATION", styles["Section"])]

    qr_flowable = Image(qr_buffer, width=31*mm, height=31*mm)
    sig_short = signature[:28] + "..." + signature[-20:] if len(signature) > 55 else signature
    sig_table = Table([
        [[qr_flowable], [
            Paragraph("<b>Signature algorithm</b>: Ed25519", styles["BodyCare"]),
            Paragraph("<b>Signature (short display)</b>", styles["BodyCare"]),
            Paragraph(sig_short, styles["SmallCare"]),
            Spacer(1, 2*mm),
            Paragraph("<b>Report SHA-256 fingerprint</b>", styles["BodyCare"]),
            Paragraph(fingerprint, styles["SmallCare"]),
            Spacer(1, 2*mm),
            Paragraph("Scan the QR code to read the signed report's verification payload. "
                      "Verify the Ed25519 signature with the CareSecure public key.",
                      styles["SmallCare"]),
        ]]],
        colWidths=[39*mm, 123*mm]
    )
    sig_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), pale),
        ("BOX", (0,0), (-1,-1), 0.6, line),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story += [sig_table, Spacer(1, 5*mm)]
    story.append(Paragraph(
        "CONFIDENTIAL MEDICAL INFORMATION — Intended only for the patient and authorised "
        "healthcare professionals. Protect this document and do not share it publicly.",
        styles["SmallCare"]
    ))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "CareSecure • Digitally signed record • Keep this report for your records",
        ParagraphStyle("FooterCare", parent=styles["SmallCare"], alignment=TA_RIGHT)
    ))

    doc.build(story)
    return buffer.getvalue()
'''
report_module.write_text(pdf_code, encoding="utf-8")
main.write_text(s, encoding="utf-8")
delivery.write_text(d, encoding="utf-8")

print("Updated files:")
print(" - main.py: professional doctor name in signed report; one-page PDF workflow")
print(" - security/delivery.py: email-only patient report delivery; Twilio not used")
print(" - security/report_pdf.py: branded A4 report with QR verification payload")
print("Backup folder:", backup)
