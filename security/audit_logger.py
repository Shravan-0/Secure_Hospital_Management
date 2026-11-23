from datetime import datetime
from database.database import connect
from security.ledger import append_ledger

def log_action(user, action, details):
    # Never include passwords, OTPs, tokens or clinical note contents.
    username = user["username"] if user else "system"
    safe_details = str(details)[:250]
    with connect() as con:
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute("INSERT INTO audit_logs(user_id,username,action,details) VALUES(?,?,?,?)",
                    (user["id"] if user else None, username, action, safe_details))
        append_ledger(con, username, action, safe_details, now)
        con.commit()
