"""Email/SMS delivery. Configure providers using environment variables; demo mode logs OTP to terminal."""
import os, smtplib, ssl, urllib.parse, urllib.request, base64
from email.message import EmailMessage

def _smtp_send(to, subject, body, attachment=None, filename=None):
    host=os.getenv("CARESECURE_SMTP_HOST"); user=os.getenv("CARESECURE_SMTP_USER"); pwd=os.getenv("CARESECURE_SMTP_PASSWORD")
    sender=os.getenv("CARESECURE_FROM_EMAIL",user or ""); port=int(os.getenv("CARESECURE_SMTP_PORT","587"))
    if not all([host,user,pwd,sender]): raise RuntimeError("Email provider is not configured. See CONFIGURATION.md.")
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=sender; msg["To"]=to; msg.set_content(body)
    if attachment: msg.add_attachment(attachment,maintype="application",subtype="pdf",filename=filename or "Patient_Report.pdf")
    with smtplib.SMTP(host, port, local_hostname="localhost", timeout=20) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(user, pwd)
        server.send_message(msg)

def send_otp(channel,destination,code):
    body=f"Your CareSecure verification code is {code}. It expires in 5 minutes. Do not share it."
    if os.getenv("CARESECURE_DEMO_MODE","1")=="1":
        print(f"\n[CARESOURCE DEMO OTP] {channel.upper()} to {destination}: {code} (5 min)\n"); return
    if channel=="email": _smtp_send(destination,"CareSecure login verification code",body); return
    if channel=="sms": send_sms(destination,body); return
    raise ValueError("Unsupported OTP channel")

def send_sms(to, body):
    sid=os.getenv("CARESECURE_TWILIO_ACCOUNT_SID"); token=os.getenv("CARESECURE_TWILIO_AUTH_TOKEN"); sender=os.getenv("CARESECURE_TWILIO_FROM")
    if not all([sid,token,sender]): raise RuntimeError("SMS provider is not configured. Set Twilio variables in .env or environment; see CONFIGURATION.md.")
    data=urllib.parse.urlencode({"To":to,"From":sender,"Body":body}).encode()
    req=urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",data=data)
    req.add_header("Authorization","Basic "+base64.b64encode(f"{sid}:{token}".encode()).decode())
    with urllib.request.urlopen(req,timeout=25) as response: response.read()

def send_patient_report(email, phone, report_text, signature, pdf_bytes):
    if email: _smtp_send(email,"Your CareSecure signed medical report","Your digitally signed medical report is attached as Patient_Report.pdf.",pdf_bytes,"Patient_Report.pdf")
    if phone:
        # SMS contains report text, signature reference and a secure URL placeholder; never put full clinical details in SMS.
        link=os.getenv("CARESECURE_PATIENT_PORTAL_URL","")
        snippet=(report_text or "").replace("\n"," ")
        body=f"CareSecure signed medical report (text copy): {snippet}\nDoctor digital signature (Ed25519): {signature}"
        if link: body += f". Secure report: {link}"
        send_sms(phone,body)
