"""RFC 6238 TOTP using only Python standard library."""
import base64, hashlib, hmac, os, struct, time

def new_secret():
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")

def totp(secret, for_time=None, step=30, digits=6):
    counter = int((time.time() if for_time is None else for_time) // step)
    key = base64.b32decode(secret + "=" * ((8-len(secret)%8)%8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0f
    code = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % (10**digits)
    return str(code).zfill(digits)

def verify_totp(secret, code, window=1):
    import time
    if not code or not str(code).isdigit(): return False
    now=time.time()
    return any(hmac.compare_digest(totp(secret, now + drift*30), str(code).zfill(6))
               for drift in range(-window, window+1))
