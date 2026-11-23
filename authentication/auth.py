from datetime import datetime, timedelta
import hashlib, secrets
from database.database import connect
from security.password_security import verify_password
from security.audit_logger import log_action
from security.delivery import send_otp

def password_stage(username, password):
    username=(username or "").strip()
    with connect() as con:
        row=con.execute("SELECT * FROM users WHERE username=? AND active=1",(username,)).fetchone()
        if row is None: return ("invalid",None,None)
        user=dict(row); attempts=int(row["failed_attempts"] or 0)
        if user.get("role") == "Doctor":
            con.execute("""
                CREATE TABLE IF NOT EXISTS doctor_access_controls (
                    user_id INTEGER PRIMARY KEY,
                    violation_count INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    last_violation_at TEXT
                )
            """)
            control = con.execute(
                "SELECT locked_until FROM doctor_access_controls WHERE user_id=?",
                (user["id"],)
            ).fetchone()
            if control and control["locked_until"]:
                try:
                    doctor_until = datetime.fromisoformat(control["locked_until"])
                    if datetime.now() < doctor_until:
                        return ("locked", None, doctor_until)
                except ValueError:
                    pass
        if row["locked_until"]:
            try:
                until=datetime.fromisoformat(row["locked_until"])
                if datetime.now()<until: return ("locked",None,until)
            except ValueError: pass
            attempts=0
        if not verify_password(password,row["password_hash"]):
            attempts+=1; locked=(datetime.now()+timedelta(hours=24)).isoformat(timespec="seconds") if attempts>=5 else None
            con.execute("UPDATE users SET failed_attempts=?,locked_until=? WHERE id=?",(attempts,locked,row["id"]))
            if locked: con.execute("INSERT INTO security_alerts(username,alert_type,details) VALUES(?,?,?)",(username,"ACCOUNT_LOCKED","Five failed password attempts; 24-hour lock"))
            con.commit(); log_action(user,"LOGIN_FAILURE","Failed password attempt")
            return ("locked",None,datetime.fromisoformat(locked)) if locked else ("invalid",None,None)
        con.execute("UPDATE users SET failed_attempts=0 WHERE id=?",(row["id"],)); con.commit()
    channels=[]
    if user.get("email"): channels.append("email")
    if user.get("phone"): channels.append("sms")
    if not channels: return ("no_contact",user,None)
    return ("choose" if len(channels)==2 else "send",user,channels)

def issue_otp(user, channel):
    channel=(channel or "").lower()
    destination=user.get("email") if channel=="email" else user.get("phone") if channel=="sms" else None
    if not destination: raise ValueError("That contact channel is not registered for this account.")
    code=f"{secrets.randbelow(1000000):06d}"
    expires=datetime.now()+timedelta(minutes=5)
    digest=hashlib.sha256((str(user["id"])+":"+code).encode()).hexdigest()
    with connect() as con:
        con.execute("UPDATE users SET otp_code_hash=?,otp_expires_at=? WHERE id=?",(digest,expires.isoformat(timespec="seconds"),user["id"]))
        con.commit()
    send_otp(channel,destination,code)
    log_action(user,"OTP_SENT",f"Login OTP sent via {channel}")
    return channel

def complete_otp(user, code):
    with connect() as con:
        row=con.execute("SELECT * FROM users WHERE id=?",(user["id"],)).fetchone()
        if not row or not row["otp_code_hash"] or not row["otp_expires_at"]: return None
        if datetime.now()>datetime.fromisoformat(row["otp_expires_at"]): return None
        digest=hashlib.sha256((str(user["id"])+":"+str(code).strip()).encode()).hexdigest()
        if not secrets.compare_digest(digest,row["otp_code_hash"]):
            log_action(dict(row),"OTP_FAILURE","Invalid OTP"); return None
        con.execute("UPDATE users SET otp_code_hash=NULL,otp_expires_at=NULL WHERE id=?",(user["id"],)); con.commit()
    result=dict(row); log_action(result,"LOGIN_SUCCESS","Password and contact OTP verified"); return result
