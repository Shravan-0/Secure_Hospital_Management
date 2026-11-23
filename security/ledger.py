"""Tamper-evident hash-chained audit ledger (not a decentralized blockchain)."""
import hashlib, json
from database.database import connect
GENESIS = "0"*64

def append_ledger(con, username, action, details, created_at):
    previous=con.execute("SELECT entry_hash FROM audit_ledger ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash=previous[0] if previous else GENESIS
    payload=json.dumps({"username":username,"action":action,"details":details,
                        "created_at":created_at,"previous_hash":prev_hash},
                       sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(payload.encode()).hexdigest()
    con.execute("""INSERT INTO audit_ledger(username,action,details,created_at,previous_hash,entry_hash)
                   VALUES(?,?,?,?,?,?)""",(username,action,details,created_at,prev_hash,digest))

def verify_ledger():
    with connect() as con:
        rows=con.execute("SELECT * FROM audit_ledger ORDER BY id").fetchall()
    previous=GENESIS
    for row in rows:
        payload=json.dumps({"username":row["username"],"action":row["action"],
            "details":row["details"],"created_at":row["created_at"],
            "previous_hash":previous},sort_keys=True,separators=(",",":"))
        if row["previous_hash"] != previous or hashlib.sha256(payload.encode()).hexdigest()!=row["entry_hash"]:
            return False, row["id"]
        previous=row["entry_hash"]
    return True, len(rows)
