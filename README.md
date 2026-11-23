# CareSecure 2.0 – Secure Hospital Management System

Educational Python desktop prototype using Tkinter + SQLite. It includes synthetic demo records and security demonstrations. **Do not use real patient data or deploy this prototype in a real hospital.**

## Quick start (Windows PowerShell)
Open PowerShell in this folder:
```powershell
python -m pip install -r requirements.txt
python verify_project.py
python main.py
```
`verify_project.py` is the one-command verification suite. It runs unit tests and checks demo accounts, database tables, signature verification and the audit hash chain. Contact OTP logic has a separate offline check. GUI workflows still need a manual check.

## Demo accounts
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Doctor 1 – Dr. Asha Rao | `doctor1` | `Doctor@123` |
| Doctor 2 – Dr. Vikram Mehta | `doctor2` | `Doctor2@123` |
| Receptionist | `reception` | `Reception@123` |

The included `database/hospital.db` contains 59 fictional patients, 2 doctors, 65 appointments and 60 fictional medical notes. Back up this file before experimenting.

## First login: configure contact details for OTP
1. Open `config/staff_contacts.json` in Notepad.
2. Enter at least one authorised email address or mobile number for each staff username.
3. Save the file and start CareSecure.
4. Sign in with username/password. If both channels are registered, choose email or mobile; if only one is registered, CareSecure uses it automatically.
5. In classroom demo mode, the OTP is printed in the PowerShell window. See `CONFIGURATION.md` to configure real SMTP and SMS delivery.

No real contact details are prefilled in this package.

## Implemented security features
- Password hashing: PBKDF2-HMAC-SHA256 with per-password random salts.
- Contact-channel OTP MFA after password verification (email and/or SMS; five-minute expiry).
- Five consecutive incorrect passwords trigger a 24-hour account lock.
- Admin Security Alerts: unlock or disable the locked account, or leave it locked. Disabling an account does not delete clinical records.
- Doctor-specific authorization: doctors can read/write only records associated with their own doctor profile and assigned appointments; authorization is enforced in service functions.
- Two-minute inactivity timeout for desktop demonstration; requires password + contact OTP again.
- SQL injection teaching lab: compares a deliberately vulnerable query in an isolated in-memory database with the application's parameterized-query pattern. The real application login remains protected.
- Ed25519 digital signatures for prescription payloads; doctor-only creation and signature verification.
- Signed PDF email and report-text/SMS delivery after explicit doctor confirmation (requires SMTP/Twilio configuration).
- SHA-256 hash-chained audit ledger with integrity verification. This is a tamper-evident local hash chain, **not a decentralized blockchain**.
- Existing audit log, input validation, parameterized SQL and RBAC.

## Prescription signing and email
Doctors can open **Prescriptions**, select a patient ID assigned to them, enter medicine/dosage instructions, and create a signed prescription. Select a prescription and choose **Verify selected prescription signature**.

A signing key pair is generated under `secure_keys/` on first use. Keep `secure_keys/prescription_ed25519_private.pem` private and back it up securely. If the private key is lost, previously signed prescriptions remain verifiable with the public key, but new signatures cannot be created with the old identity.

Email is optional and requires SMTP configuration through environment variables (never put credentials in source code):
- `CARESECURE_SMTP_HOST`
- `CARESECURE_SMTP_PORT` (usually `587`)
- `CARESECURE_SMTP_USER`
- `CARESECURE_SMTP_PASSWORD`
- `CARESECURE_FROM_EMAIL`

The patient must have at least one contact method recorded. The doctor is asked before sending. TLS is used for SMTP email. Use a test mailbox and fictional patient addresses for the classroom demonstration. The signed PDF is a demonstration document, not a clinically valid prescription.

## Audit ledger
The Audit Ledger page verifies that each audit event's SHA-256 hash links to the preceding entry. It detects changes to entries within the stored chain. This local hash chain does not prevent a privileged person with full database/file access from replacing the entire database or rebuilding the chain. External signed checkpoints or independent storage would be needed for stronger guarantees.

## SQL injection demonstration
Admin > SQL Injection Lab runs an intentionally vulnerable query only against a disposable in-memory teaching database and compares it with parameterized SQL. Do not test random public websites or systems without written permission.

## Tests and database
```powershell
python verify_project.py
python -m unittest discover -s tests -v
```
Database: `database/hospital.db`. Existing demo data is included. `python main.py` initializes/migrates the database without deleting patient data.

## Important limitations
This is a local, single-computer educational prototype. It is not production-ready. It does not provide a hospital-grade key management system, encryption at rest, regulatory compliance, multi-user concurrency controls, secure remote access, clinical decision support or validated medical workflows. Review privacy, legal, clinical and security requirements before any real deployment.


## CareSecure 3.0 – contact OTP update

- Staff sign in with password + OTP by email or SMS. If both are registered, choose a channel; if only one is registered, it is selected automatically.
- The local staff contact registry is `config/staff_contacts.json`. Fill it with authorised contact details, at least one per account, then restart the app.
- Reception must provide at least one patient email/mobile.
- Signed report delivery uses PDF email and SMS summary/signature reference. SMS requires an SMS provider; PDF email requires SMTP.
- Demo mode prints OTPs in the PowerShell terminal. See `CONFIGURATION.md` before enabling real delivery.
- Keep `config/staff_contacts.json`, the SQLite database, and provider credentials private.
