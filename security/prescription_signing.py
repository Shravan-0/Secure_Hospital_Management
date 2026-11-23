"""Ed25519 signing helpers. Requires cryptography package."""
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEY_DIR=Path("secure_keys")
PRIVATE=KEY_DIR/"prescription_ed25519_private.pem"
PUBLIC=KEY_DIR/"prescription_ed25519_public.pem"

def ensure_keys():
    KEY_DIR.mkdir(exist_ok=True)
    if not PRIVATE.exists():
        key=Ed25519PrivateKey.generate()
        PRIVATE.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        PUBLIC.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
        try: PRIVATE.chmod(0o600)
        except OSError: pass

def sign_payload(payload):
    ensure_keys()
    key=serialization.load_pem_private_key(PRIVATE.read_bytes(),password=None)
    return key.sign(payload.encode()).hex()

def verify_payload(payload, signature):
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    ensure_keys()
    key=serialization.load_pem_public_key(PUBLIC.read_bytes())
    try: key.verify(bytes.fromhex(signature),payload.encode()); return True
    except (InvalidSignature,ValueError): return False
