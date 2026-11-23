import unittest
from security.password_security import hash_password, verify_password
from security.access_control import allowed
from security.validation import validate_patient, validate_date_time

class SecurityTests(unittest.TestCase):
    def test_password_hash_and_verify(self):
        stored = hash_password("Example@123")
        self.assertNotEqual(stored, "Example@123")
        self.assertTrue(verify_password("Example@123", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_role_permissions(self):
        self.assertTrue(allowed("Admin", "logs.read"))
        self.assertFalse(allowed("Receptionist", "logs.read"))
        self.assertFalse(allowed("Doctor", "users.manage"))

    def test_patient_validation(self):
        self.assertEqual(validate_patient("Test Patient", "20", "9876543210")[1], 20)
        with self.assertRaises(ValueError):
            validate_patient("", "20", "123")

    def test_date_validation(self):
        validate_date_time("2026-11-15", "10:30")
        with self.assertRaises(ValueError):
            validate_date_time("15/11/2026", "25:90")


    def test_totp_round_trip(self):
        from security.mfa import new_secret, totp, verify_totp
        secret = new_secret()
        self.assertTrue(verify_totp(secret, totp(secret)))

    def test_ed25519_signature(self):
        from security.prescription_signing import sign_payload, verify_payload
        message = "patient=demo|medicine=sample"
        signature = sign_payload(message)
        self.assertTrue(verify_payload(message, signature))
        self.assertFalse(verify_payload(message + "|altered", signature))

if __name__ == "__main__":
    unittest.main()
