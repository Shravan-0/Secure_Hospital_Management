# CareSecure – Secure Hospital Management System

## Abstract
CareSecure is an educational Python desktop prototype that demonstrates selected Secure Software Engineering practices in a hospital workflow. It provides administrator, doctor and receptionist roles, patient registration, appointment scheduling, basic consultation notes and an audit view. The application uses password hashing, role-based authorization, input validation and parameterized database queries.

## Problem statement
Hospital workflows involve personal and medical information. If every staff member can access every function, information may be disclosed or changed without authorization. The project demonstrates how security requirements can be incorporated into a small software system.

## Objectives
1. Build a simple desktop application for selected hospital workflows.
2. Separate administrator, doctor and receptionist permissions.
3. Avoid plaintext password storage.
4. Validate important user input.
5. Record important security-relevant actions.
6. test authorization and validation behaviour.

## Scope
Included: login, staff roles, patient registration, appointment scheduling, doctor consultation notes, audit activity and basic security tests.
Excluded: billing, pharmacy, laboratory, insurance, patient portal, cloud deployment and real clinical use.

## Roles
- Administrator: manage staff accounts, view patients, appointments, medical records and audit activity.
- Doctor: view patients and appointments assigned to that doctor; create and view own consultation notes.
- Receptionist: register and search patients and schedule appointments; cannot access consultation notes.

## Secure engineering lifecycle mapping
### Unit I – Software engineering and process
The work is divided into small modules and developed iteratively: authentication, patient workflow, appointments, consultation records, then testing and documentation. Ethical handling of sensitive information is considered in the project scope.

### Unit II – Requirements engineering
Functional requirements:
- Users can sign in with valid credentials.
- Receptionists can register patients and schedule appointments.
- Doctors can view assigned appointments and add consultation notes.
- Administrators can create staff accounts and view audit activity.
Non-functional/security requirements:
- Passwords are not stored in plaintext.
- Unauthorized role actions are rejected by service-layer permission checks.
- Invalid patient and appointment input is rejected.
- Important actions are recorded without logging passwords or clinical note contents.

### Unit III – Secure SDLC
- Least privilege: receptionist, doctor and administrator have different permissions.
- Defence in depth: authentication, service-layer authorization, input validation, database constraints and audit logging are used together.
- STRIDE examples:
  - Spoofing: stolen or guessed credentials; mitigate with password hashing and login checks.
  - Tampering: unauthorized record changes; mitigate with permission checks and audit events.
  - Repudiation: user denies an action; mitigate with timestamped audit records.
  - Information disclosure: receptionist attempts to view clinical notes; mitigate with role restrictions.
  - Denial of service: repeated login attempts; identified as a risk for future rate limiting.
  - Elevation of privilege: receptionist attempts administrator operations; mitigate with server/service-layer authorization checks.
- Risk treatment: the prototype prioritizes confidentiality of consultation notes and account access.

### Unit IV – Architecture, verification and testing
The GUI calls application service functions. Service functions perform role checks and validation before parameterized SQLite operations. The test suite covers password verification, role permissions and input validation. Manual demonstration includes attempting to use restricted functions with the wrong role.

### Unit V – DevSecOps
A simple workflow is proposed: keep source in Git, run unit tests on changes, run Bandit static analysis, use pip-audit for dependency checks, review code changes and retain a dependency list as a basic SBOM. The core application uses Python standard-library modules; optional tools are listed in requirements.txt.

## Architecture summary
Tkinter presentation layer → authentication and application services → authorization and validation checks → SQLite data store. Audit events are written through a dedicated audit logger. Sensitive operations are checked in service functions, not merely hidden in the interface.

## Test summary
Run `python -m unittest discover -s tests -v`. The included tests verify password hash/verify behaviour, role permission decisions, patient input validation and appointment date/time validation. Record the actual output from the demonstration machine in the final submission; do not claim tests passed until run there.

## Conclusion
CareSecure demonstrates that security requirements can shape design and implementation even in a small desktop application. It is a teaching prototype, not a production hospital information system.
