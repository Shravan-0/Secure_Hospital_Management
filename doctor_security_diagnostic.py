import sqlite3

db = sqlite3.connect("database/hospital.db")
db.row_factory = sqlite3.Row

print("\n===== DATABASE TABLES =====")
tables = [r["name"] for r in db.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)]
for table in tables:
    print(table)

print("\n===== RELEVANT TABLE SCHEMAS =====")
for table in ["users", "security_alerts", "appointments", "audit_logs"]:
    if table in tables:
        print(f"\n{table}:")
        for col in db.execute(f"PRAGMA table_info({table})"):
            print(dict(col))

print("\n===== DOCTOR ACCOUNTS =====")
for row in db.execute("""
    SELECT u.id, u.username, u.role, u.failed_attempts,
           u.locked_until, d.id AS doctor_id, d.name AS doctor_name
    FROM users u
    LEFT JOIN doctors d ON d.user_id = u.id
    WHERE lower(u.role) = 'doctor'
"""):
    print(dict(row))

db.close()
print("\nDATABASE DIAGNOSTIC COMPLETE")
