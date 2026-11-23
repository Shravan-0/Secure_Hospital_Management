# CareSecure contact and delivery configuration

## Staff contact details (local file)

Open `config/staff_contacts.json` in Notepad. Fill in at least one contact method for each staff account. Example only:

```json
{
  "admin": {"email": "admin@example.com", "phone": "+919876543210"},
  "doctor1": {"email": "", "phone": "+919876543211"},
  "doctor2": {"email": "doctor2@example.com", "phone": ""},
  "reception": {"email": "reception@example.com", "phone": ""}
}
```

Use your own authorised contact details; the example values are fictional. Save the file and restart CareSecure. Admin can create new users in User management and enter email/mobile there. For an existing account, add its username as a JSON key. Do not commit this file to a public repository.

## Patient contacts

Reception enters email and/or mobile in Patients. At least one is required. Existing patients can be updated directly in the local SQLite database using a trusted database editor, or through a future patient-edit screen. Never upload real patient data to public repositories.

## OTP and delivery modes

By default `CARESECURE_DEMO_MODE=1`: OTPs are printed to the PowerShell window for classroom demonstration and no message is sent. Change it to `0` only after configuring delivery providers.

Email environment variables: `CARESECURE_SMTP_HOST`, `CARESECURE_SMTP_PORT` (usually 587), `CARESECURE_SMTP_USER`, `CARESECURE_SMTP_PASSWORD`, `CARESECURE_FROM_EMAIL`.

SMS environment variables (Twilio): `CARESECURE_TWILIO_ACCOUNT_SID`, `CARESECURE_TWILIO_AUTH_TOKEN`, `CARESECURE_TWILIO_FROM`. Set `CARESECURE_PATIENT_PORTAL_URL` to your HTTPS patient portal URL if one exists. SMS includes a short summary/signature reference; it is not a replacement for the signed PDF.

Never place SMTP or SMS credentials in Python source or the ZIP. Set them as Windows environment variables on the machine that sends messages. A secure patient report link requires a real authenticated HTTPS portal; do not expose a local file path or public unauthenticated link.
