"""One-command CareSecure verification. Does not modify patient/clinical data."""
import sys, unittest
from database.database import initialize, connect
from security.password_security import verify_password
from security.mfa import new_secret, totp, verify_totp
from security.ledger import verify_ledger
from security.prescription_signing import sign_payload, verify_payload

def main():
    initialize()
    suite=unittest.defaultTestLoader.discover("tests")
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): return 1
    with connect() as con:
        users=con.execute("SELECT username,password_hash,role,active FROM users").fetchall()
        counts={t:con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("patients","doctors","appointments","medical_records","audit_logs")}
        schema=con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    accounts={r["username"]:r for r in users}
    checks=[
        ("Admin demo password", "admin" in accounts and verify_password("Admin@123",accounts["admin"]["password_hash"])),
        ("Doctor 1 account", "doctor1" in accounts),
        ("Doctor 2 account", "doctor2" in accounts),
        ("Reception account", "reception" in accounts),
        ("MFA TOTP generation/verification", (lambda s: verify_totp(s,totp(s)))(new_secret())),
        ("Ed25519 prescription signature", (lambda p: verify_payload(p,sign_payload(p)))("CareSecure test prescription")),
        ("Tamper-evident audit ledger", verify_ledger()[0]),
        ("Security alerts schema", any(r["name"]=="security_alerts" for r in schema)),
        ("Prescription schema", any(r["name"]=="prescriptions" for r in schema)),
    ]
    failed=False
    for label,ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        failed |= not ok
    print("\nDatabase totals:")
    for key,value in counts.items(): print(f"  {key}: {value}")
    print("\nNote: GUI workflows, real SMTP/SMS delivery and inactivity timing require manual desktop verification. Contact OTP logic has a separate offline test in verify_contact_mfa.py.")
    return 1 if failed else 0

if __name__=="__main__":
    sys.exit(main())
