# Short STRIDE threat analysis

| STRIDE category | Example in CareSecure | Current control | Residual / future work |
|---|---|---|---|
| Spoofing | Attacker guesses a staff password | PBKDF2 password hashing and credential verification | Add login throttling and MFA |
| Tampering | User changes a patient record without authority | Service-layer role checks and audit events | Add immutable/append-only audit storage |
| Repudiation | Staff member denies making a change | Timestamped username/action audit record | Add tamper-evident log chaining |
| Information disclosure | Receptionist reads consultation notes | No medical-record view for receptionist; role checks | Add encryption at rest and finer patient consent rules |
| Denial of service | Repeated login attempts | Generic login error; no technical detail exposed | Add rate limiting and monitoring |
| Elevation of privilege | Receptionist invokes admin service function | `require()` checks in service functions | Add centralized permission review and security regression tests |

This is a classroom threat model, not a formal security assessment.
