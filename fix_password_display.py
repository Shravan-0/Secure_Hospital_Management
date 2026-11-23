from pathlib import Path
import shutil

p = Path("main.py")
s = p.read_text(encoding="utf-8-sig")

if "â€¢" not in s:
    print("The corrupted masking character was not found.")
else:
    shutil.copy2(p, "main.py.encoding-backup")
    s = s.replace('show="â€¢"', 'show="*"')
    s = s.replace('show="â€¢" if label=="Temporary password" else ""',
                  'show="*" if label=="Temporary password" else ""')
    p.write_text(s, encoding="utf-8")
    print("Password masking fixed. Backup: main.py.encoding-backup")

compile(s, str(p), "exec")
print("Syntax check: PASSED")
