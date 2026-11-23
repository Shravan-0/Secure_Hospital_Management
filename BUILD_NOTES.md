# CareSecure 3.0 build notes

This package was built from the supplied CareSecure 2.0 project and its included database. Existing database rows were retained: 59 patients, 2 doctors, 65 appointments, 60 medical records, and 30 original audit log entries at packaging time.

Staff contact details are intentionally blank. Enter them in `config/staff_contacts.json`; do not upload real personal contact details to public repos or chats. Patient contact details are entered through the Receptionist patient form.

Automated checks run during packaging:
- `python -m compileall -q .`
- `python verify_contact_mfa.py` (isolated test database/workflow; no real messages)
- `python verify_project.py` (6 unit tests and database/security checks)

Real email/SMS delivery, GUI workflows, report delivery and timeout behaviour still require manual testing on the target Windows computer with provider credentials configured. This is an educational desktop prototype, not a production clinical system.
