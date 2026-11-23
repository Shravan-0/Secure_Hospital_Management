# CareSecure 2.0 – Security Upgrade and Demonstration Guide

## Attack / protection demonstrations

1. **MFA:** first login displays a TOTP setup secret. Enroll in an authenticator app, then demonstrate that password alone is insufficient.
2. **Doctor authorization:** create/assign appointments to different doctors. Doctor-specific record queries and writes check the authenticated doctor profile and appointment assignment. Try a patient ID belonging only to the other doctor; access must be denied.
3. **Brute force:** enter a wrong password five times for a demo account. The account receives a 24-hour lock and an Admin alert. Admin can unlock or disable the account. “Do nothing” leaves it locked.
4. **SQL injection:** Admin > SQL Injection Lab compares a deliberately unsafe query in a disposable in-memory database with parameterized SQL. The production login never uses the unsafe query.
5. **Prescription authenticity:** Doctor creates a prescription. The app signs the canonical prescription payload using Ed25519. Select it and verify. Altering the payload in a test copy makes verification fail.
6. **Session timeout:** leave the desktop app inactive for two minutes. It signs out and requires password plus OTP again.
7. **Audit integrity:** Admin > Audit Ledger verifies the SHA-256 hash chain. Any edit to a chained row is detected.

## Admin lock alert actions
- Unlock: clears failed count and lock timestamp.
- Disable: sets the account inactive; does not delete patient or clinical records.
- Do nothing: leaves the lock in place.

## Email report delivery
Patient registration accepts an optional email address. Doctor creates and signs a prescription, then explicitly chooses whether to send it. SMTP settings are read from environment variables and sent over STARTTLS. Use synthetic patient details and a test mailbox.

## Verification
Run `python verify_project.py`. This runs six unit tests and checks the demo accounts, TOTP, Ed25519 signatures, schema and audit chain. It does not automate graphical interaction, authenticator enrollment or external SMTP delivery; those require manual verification.
