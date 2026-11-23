from pathlib import Path
import re

for filename in ["modules/services.py", "main.py", "authentication/auth.py"]:
    p = Path(filename)
    print("\n" + "=" * 25, filename, "=" * 25)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

    if filename == "main.py":
        # Show all method definitions and the relevant security/access methods.
        for i, line in enumerate(lines):
            if re.match(r"\s+def ", line):
                print(f"{i+1}: {line.strip()}")
        print("\n--- Patient, appointment and medical-record access references ---")
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in
                   ["patient", "medical_records", "appointments", "resolve_alert", "alerts_page"]):
                start, end = max(0, i-2), min(len(lines), i+4)
                print(f"\nLines {start+1}-{end}:")
                for j in range(start, end):
                    print(f"{j+1}: {lines[j]}")
    else:
        for i, line in enumerate(lines):
            print(f"{i+1}: {line}")
