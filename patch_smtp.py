from pathlib import Path
import shutil

p = Path("security/delivery.py")
if not p.exists():
    raise SystemExit("ERROR: security/delivery.py not found. Run this from the project folder.")

source = p.read_text(encoding="utf-8-sig")

old_import = "import os, smtplib, urllib.parse, urllib.request, base64"
new_import = "import os, smtplib, ssl, urllib.parse, urllib.request, base64"

old_smtp = "with smtplib.SMTP(host,port,timeout=20) as server: server.starttls(); server.login(user,pwd); server.send_message(msg)"

new_smtp = '''with smtplib.SMTP(host, port, local_hostname="localhost", timeout=20) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(user, pwd)
        server.send_message(msg)'''

if new_smtp in source:
    print("SMTP patch already installed.")
else:
    if old_smtp not in source:
        raise SystemExit("ERROR: Expected SMTP code not found. No file changed.")
    if old_import not in source:
        raise SystemExit("ERROR: Expected import line not found. No file changed.")

    backup = p.with_suffix(".py.backup")
    shutil.copy2(p, backup)
    source = source.replace(old_import, new_import, 1)
    source = source.replace(old_smtp, new_smtp, 1)
    p.write_text(source, encoding="utf-8")
    print("SMTP code patched successfully.")
    print("Backup:", backup)

compile(source, str(p), "exec")
print("Python syntax check: PASSED")
