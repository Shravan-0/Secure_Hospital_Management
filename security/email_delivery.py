"""Optional TLS email delivery. Configure credentials through environment variables."""
import os, smtplib
from email.message import EmailMessage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

def send_prescription_email(recipient, payload, signature):
    host=os.getenv("CARESECURE_SMTP_HOST")
    port=int(os.getenv("CARESECURE_SMTP_PORT","587"))
    username=os.getenv("CARESECURE_SMTP_USER")
    password=os.getenv("CARESECURE_SMTP_PASSWORD")
    sender=os.getenv("CARESECURE_FROM_EMAIL",username or "")
    if not all([host,username,password,sender]):
        raise RuntimeError("Email is not configured. Set CARESECURE_SMTP_HOST, CARESECURE_SMTP_PORT, CARESECURE_SMTP_USER, CARESECURE_SMTP_PASSWORD and CARESECURE_FROM_EMAIL.")
    buf=BytesIO()
    pdf=canvas.Canvas(buf,pagesize=A4)
    pdf.setTitle("CareSecure Signed Prescription")
    y=800
    for line in ["CareSecure - Digitally Signed Prescription","",*payload.split("|"),"",
                 "Ed25519 signature (hex):",signature]:
        pdf.drawString(45,y,str(line)[:115]); y-=22
        if y<70: pdf.showPage(); y=800
    pdf.save()
    msg=EmailMessage()
    msg["Subject"]="Your CareSecure medical prescription"
    msg["From"]=sender; msg["To"]=recipient
    msg.set_content("Your doctor has sent a digitally signed prescription. The attached PDF includes its signature.")
    msg.add_attachment(buf.getvalue(),maintype="application",subtype="pdf",filename="CareSecure_Prescription.pdf")
    with smtplib.SMTP(host,port,timeout=20) as server:
        server.starttls()
        server.login(username,password)
        server.send_message(msg)
