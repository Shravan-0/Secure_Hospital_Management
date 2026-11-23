from load_env import load_env
load_env()

import tkinter as tk
from tkinter import ttk, messagebox
from database.database import initialize, connect
from authentication.auth import password_stage, issue_otp, complete_otp
from modules import services

BG = "#F3F6FA"
NAVY = "#17324D"
TEAL = "#087E8B"

class CareSecureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CareSecure | Hospital Management")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self.user = None
        self.pending_user = None
        self.pending_secret = None
        self.pending_channels = []
        self.pending_channel = None
        self.last_activity = __import__("time").time()
        self.root.bind_all("<Key>", self._touch)
        self.root.bind_all("<Button>", self._touch)
        self.root.after(15000, self._check_idle)
        self.login_screen()

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def login_screen(self):
        self.clear()
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(expand=True, fill="both")
        card = tk.Frame(wrap, bg="white", padx=42, pady=36, highlightbackground="#DCE4EC", highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center")
        tk.Label(card, text="CARESECURE", bg="white", fg=NAVY, font=("Segoe UI", 22, "bold")).pack()
        tk.Label(card, text="Secure Hospital Management", bg="white", fg="#64748B",
                 font=("Segoe UI", 10)).pack(pady=(4,24))
        tk.Label(card, text="Username", bg="white", fg=NAVY).pack(anchor="w")
        self.username = ttk.Entry(card, width=36, font=("Segoe UI", 11))
        self.username.pack(pady=(5,14), ipady=6)
        tk.Label(card, text="Password", bg="white", fg=NAVY).pack(anchor="w")
        self.password = ttk.Entry(card, width=36, show="*", font=("Segoe UI", 11))
        self.password.pack(pady=(5,20), ipady=6)
        ttk.Button(card, text="Sign in", command=self.do_login).pack(fill="x", ipady=5)
        tk.Label(card, text="Demo accounts are listed in README.md", bg="white",
                 fg="#64748B", font=("Segoe UI", 9)).pack(pady=(18,0))
        self.password.bind("<Return>", lambda e: self.do_login())
        self.username.focus_set()

    def _touch(self, event=None):
        self.last_activity = __import__("time").time()

    def _check_idle(self):
        if self.user and __import__("time").time()-self.last_activity >= 120:
            from security.audit_logger import log_action
            log_action(self.user,"SESSION_TIMEOUT","Logged out after 2 minutes of inactivity")
            self.user=None
            messagebox.showwarning("Session expired","You were signed out after inactivity. Sign in again with password and OTP.")
            self.login_screen()
        self.root.after(15000,self._check_idle)

    def do_login(self):
        status,user,extra = password_stage(self.username.get(), self.password.get())
        if status == "locked":
            messagebox.showerror("Account locked",f"Account locked until {extra}. Contact the administrator."); return
        if status == "invalid":
            messagebox.showerror("Sign in failed","Invalid username or password."); return
        if status == "no_contact":
            messagebox.showerror("Contact details required","Ask the administrator to add an email address or mobile number to this account."); return
        self.pending_user=user; self.pending_channels=extra
        if status == "choose": self.channel_screen(); return
        try:
            self.pending_channel=extra[0]; issue_otp(user,self.pending_channel); self.otp_screen()
        except Exception as exc: messagebox.showerror("OTP delivery failed",str(exc))

    def channel_screen(self):
        self.clear(); card=tk.Frame(self.root,bg="white",padx=38,pady=30); card.place(relx=.5,rely=.5,anchor="center")
        tk.Label(card,text="CHOOSE OTP DELIVERY",bg="white",fg=NAVY,font=("Segoe UI",16,"bold")).pack(pady=10)
        tk.Label(card,text="Both email and mobile are registered. Choose one channel.",bg="white").pack(pady=8)
        ttk.Button(card,text="Send OTP to email",command=lambda:self.send_selected("email")).pack(fill="x",pady=5)
        ttk.Button(card,text="Send OTP to mobile",command=lambda:self.send_selected("sms")).pack(fill="x",pady=5)
        ttk.Button(card,text="Cancel",command=self.login_screen).pack(fill="x",pady=5)

    def send_selected(self,channel):
        try:
            self.pending_channel=channel; issue_otp(self.pending_user,channel); self.otp_screen()
        except Exception as exc: messagebox.showerror("OTP delivery failed",str(exc))

    def otp_screen(self):
        self.clear(); card=tk.Frame(self.root,bg="white",padx=38,pady=30); card.place(relx=.5,rely=.5,anchor="center")
        tk.Label(card,text="MULTI-FACTOR VERIFICATION",bg="white",fg=NAVY,font=("Segoe UI",16,"bold")).pack(pady=8)
        destination=self.pending_user.get("email") if self.pending_channel=="email" else self.pending_user.get("phone")
        masked=(destination[:2]+"***"+destination[-8:]) if destination and len(destination)>10 else destination
        tk.Label(card,text=f"A one-time code was sent via {self.pending_channel.upper()} to {masked}.",bg="white",wraplength=420).pack(pady=8)
        tk.Label(card,text="The code expires in 5 minutes.",bg="white",fg="#64748B").pack()
        code=ttk.Entry(card,width=24,justify="center",font=("Segoe UI",16)); code.pack(pady=12)
        ttk.Button(card,text="Verify OTP",command=lambda:self.finish_otp(code.get())).pack(fill="x",ipady=5)
        ttk.Button(card,text="Cancel",command=self.login_screen).pack(fill="x",pady=6)

    def finish_otp(self,code):
        user=complete_otp(self.pending_user,code.strip())
        if not user:
            messagebox.showerror("OTP failed","Invalid or expired OTP. Request a new code by signing in again."); return
        self.user=user; self._touch(); self.dashboard()

    def dashboard(self):
        self.clear()
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg=NAVY, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="CARESECURE", bg=NAVY, fg="white",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20, pady=(28,3))
        tk.Label(side, text=f"{self.user['role']} workspace", bg=NAVY, fg="#B8CAD9",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(0,28))
        self.content = tk.Frame(shell, bg=BG, padx=28, pady=24)
        self.content.pack(side="left", fill="both", expand=True)
        menu = [
            ("Overview", self.overview),
            ("Patients", self.patient_page),
            ("Appointments", self.appointment_page),
        ]
        if self.user["role"] in ("Doctor", "Admin"):
            menu.append(("Medical records", self.records_page))
        if self.user["role"] == "Admin":
            menu.extend([("User management", self.users_page), ("Security alerts", self.alerts_page),
                         ("Security activity", self.logs_page), ("SQL injection lab", self.sql_lab),
                         ("Audit ledger", self.ledger_page)])
        if self.user["role"] == "Doctor":
            menu.append(("Prescriptions", self.prescription_page))
        for label, fn in menu:
            ttk.Button(side, text=label, command=fn).pack(fill="x", padx=14, pady=5, ipady=5)
        ttk.Button(side, text="Sign out", command=self.logout).pack(side="bottom", fill="x", padx=14, pady=18, ipady=5)
        self.overview()

    def heading(self, title, subtitle=""):
        for w in self.content.winfo_children(): w.destroy()
        tk.Label(self.content, text=title, bg=BG, fg=NAVY,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(self.content, text=subtitle, bg=BG, fg="#64748B",
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(3,18))

    def table(self, columns, rows, headings=None):
        frame = tk.Frame(self.content, bg="white", padx=12, pady=12)
        frame.pack(fill="both", expand=True, pady=10)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        for c in columns:
            tree.heading(c, text=(headings or {}).get(c, c.replace("_"," ").title()))
            tree.column(c, width=145, anchor="w")
        for row in rows:
            tree.insert("", "end", values=tuple(row[c] if isinstance(row, dict) else row[i] for i,c in enumerate(columns)))
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    def overview(self):
        self.heading(f"Welcome, {self.user['username']}", "Hospital operations at a glance")
        p,a,d = services.dashboard_counts(self.user)
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=10)
        for label, value in [("Patients",p),("Appointments",a),("Doctors",d)]:
            card = tk.Frame(cards, bg="white", padx=24, pady=22, highlightbackground="#E0E7EF", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0,12))
            tk.Label(card, text=str(value), bg="white", fg=TEAL, font=("Segoe UI",25,"bold")).pack(anchor="w")
            tk.Label(card, text=label, bg="white", fg="#64748B", font=("Segoe UI",10)).pack(anchor="w")
        note = tk.Frame(self.content, bg="white", padx=20, pady=18)
        note.pack(fill="x", pady=18)
        tk.Label(note, text="Security at a glance", bg="white", fg=NAVY,
                 font=("Segoe UI",14,"bold")).pack(anchor="w")
        tk.Label(note, text="Access is controlled by role. Passwords are hashed. Sensitive actions are recorded in the audit log.",
                 bg="white", fg="#475569", wraplength=760, justify="left").pack(anchor="w", pady=8)
        tk.Label(note, text=f"Signed in as {self.user['role']}. Only authorized modules are shown.",
                 bg="white", fg=TEAL).pack(anchor="w")

    def patient_page(self):
        self.heading("Patient management", "Register and find patient records")
        if self.user["role"] in ("Admin","Receptionist"):
            form = tk.Frame(self.content, bg="white", padx=14, pady=12)
            form.pack(fill="x", pady=(0,10))
            entries = []
            for label in ("Full name","Age","Phone","Email"):
                tk.Label(form, text=label, bg="white", fg=NAVY).pack(side="left", padx=(0,5))
                e = ttk.Entry(form, width=17); e.pack(side="left", padx=(0,12)); entries.append(e)
            ttk.Button(form, text="Add patient", command=lambda: self.add_patient(*[e.get() for e in entries])).pack(side="left")
        rows = services.patients(self.user)
        self.table(("id","full_name","age","phone","email","created_at"), rows)

    def add_patient(self, name, age, phone, email=""):
        try:
            pid = services.add_patient(self.user, name, age, phone, email)
            messagebox.showinfo("Saved", f"Patient registered. Patient ID: {pid}")
            self.patient_page()
        except Exception as e: messagebox.showerror("Cannot save patient", str(e))

    def appointment_page(self):
        self.heading("Appointments", "View and schedule appointments")
        if self.user["role"] in ("Admin","Receptionist"):
            form = tk.Frame(self.content, bg="white", padx=14, pady=12)
            form.pack(fill="x", pady=(0,10))
            with connect() as con:
                pats = con.execute("SELECT id,full_name FROM patients ORDER BY full_name").fetchall()
            docs = services.doctors()
            tk.Label(form,text="Patient",bg="white").grid(row=0,column=0,padx=5)
            pbox=ttk.Combobox(form,state="readonly",width=22,values=[f"{r['id']} - {r['full_name']}" for r in pats]); pbox.grid(row=0,column=1,padx=5)
            tk.Label(form,text="Doctor",bg="white").grid(row=0,column=2,padx=5)
            dbox=ttk.Combobox(form,state="readonly",width=22,values=[f"{r['id']} - {r['name']}" for r in docs]); dbox.grid(row=0,column=3,padx=5)
            tk.Label(form,text="Date YYYY-MM-DD",bg="white").grid(row=1,column=0,pady=8)
            date=ttk.Entry(form,width=24); date.grid(row=1,column=1)
            tk.Label(form,text="Time HH:MM",bg="white").grid(row=1,column=2)
            time=ttk.Entry(form,width=24); time.grid(row=1,column=3)
            ttk.Button(form,text="Book appointment",command=lambda:self.add_appointment(pbox.get(),dbox.get(),date.get(),time.get())).grid(row=1,column=4,padx=8)
        self.table(("id","full_name","doctor","appt_date","appt_time","status"), services.appointments(self.user))

    def add_appointment(self, patient, doctor, date, time):
        try:
            if not patient or not doctor: raise ValueError("Select a patient and doctor.")
            pid=int(patient.split(" - ")[0]); did=int(doctor.split(" - ")[0])
            aid=services.add_appointment(self.user,pid,did,date.strip(),time.strip())
            messagebox.showinfo("Booked",f"Appointment created. ID: {aid}")
            self.appointment_page()
        except Exception as e: messagebox.showerror("Cannot book appointment",str(e))

    def records_page(self):
        self.heading("Medical records", "Consultation information is restricted to authorized clinical users")
        if self.user["role"] == "Doctor":
            form=tk.Frame(self.content,bg="white",padx=14,pady=12); form.pack(fill="x",pady=(0,10))
            tk.Label(form,text="Patient ID",bg="white").grid(row=0,column=0,padx=5)
            pid=ttk.Entry(form,width=12); pid.grid(row=0,column=1,padx=5)
            tk.Label(form,text="Consultation notes",bg="white").grid(row=0,column=2,padx=5)
            notes=ttk.Entry(form,width=45); notes.grid(row=0,column=3,padx=5)
            ttk.Button(form,text="Save notes",command=lambda:self.save_record(pid.get(),notes.get())).grid(row=0,column=4,padx=5)
            rows=services.records_for_doctor(self.user)
            self.table(("id","full_name","notes","created_at"),rows)
        else:
            self.table(("id","patient_id","doctor_id","notes","created_at"),
                       self.admin_records())

    def admin_records(self):
        from security.access_control import require
        require(self.user["role"],"records.read_all")
        with connect() as con:
            return con.execute("SELECT id,patient_id,doctor_id,notes,created_at FROM medical_records ORDER BY id DESC").fetchall()

    def save_record(self,pid,notes):
        try:
            services.add_record(self.user,pid,notes)
            messagebox.showinfo("Saved","Consultation note saved.")
            self.records_page()
        except Exception as e: messagebox.showerror("Cannot save record",str(e))

    def users_page(self):
        self.heading("User management", "Create staff accounts (administrator only)")
        form=tk.Frame(self.content,bg="white",padx=14,pady=14); form.pack(fill="x",pady=(0,10))
        fields=[]
        for label in ("Username","Temporary password","Role","Doctor display name","Email","Mobile"):
            tk.Label(form,text=label,bg="white").pack(side="left",padx=(0,4))
            if label=="Role":
                w=ttk.Combobox(form,values=["Doctor","Receptionist","Admin"],state="readonly",width=13); w.set("Receptionist")
            else: w=ttk.Entry(form,width=16,show="*" if label=="Temporary password" else "")
            w.pack(side="left",padx=(0,8)); fields.append(w)
        ttk.Button(form,text="Create account",command=lambda:self.create_user(fields)).pack(side="left")
        with connect() as con: rows=con.execute("SELECT id,username,role,email,phone,active FROM users ORDER BY id").fetchall()
        self.table(("id","username","role","email","phone","active"),rows)

    def create_user(self,fields):
        try:
            services.create_user(self.user,fields[0].get(),fields[1].get(),fields[2].get(),fields[3].get(), email=fields[4].get(), phone=fields[5].get())
            messagebox.showinfo("Created","Staff account created.")
            self.users_page()
        except Exception as e: messagebox.showerror("Cannot create account",str(e))

    def logs_page(self):
        self.heading("Security activity", "Recent sign-ins and important actions; sensitive clinical note contents are not logged")
        rows=services.audit_logs(self.user)
        self.table(("created_at","username","action","details"),rows)

    def alerts_page(self):
        self.heading("Security alerts","Accounts locked after five failed password attempts")
        with connect() as con:
            rows=con.execute("SELECT id,username,details,created_at,status FROM security_alerts WHERE status='Open' ORDER BY id DESC").fetchall()
        tree=self.table(("id","username","details","created_at","status"),rows)
        bar=tk.Frame(self.content,bg=BG); bar.pack(fill="x",pady=8)
        ttk.Button(bar,text="Unlock selected account",command=lambda:self.resolve_alert(tree,"unlock")).pack(side="left",padx=4)
        ttk.Button(bar,text="Delete selected account",command=lambda:self.resolve_alert(tree,"delete")).pack(side="left",padx=4)
        ttk.Button(bar,text="Do nothing",command=self.alerts_page).pack(side="left",padx=4)

    def resolve_alert(self,tree,action):
        selected=tree.selection()
        if not selected: messagebox.showwarning("Select alert","Choose an alert first."); return
        vals=tree.item(selected[0],"values"); alert_id=int(vals[0]); username=vals[1]
        if action=="delete" and not messagebox.askyesno("Confirm deletion",f"Disable account {username}? Patient and clinical records will be preserved."): return
        with connect() as con:
            if action=="unlock":
                con.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE username=?",(username,))
                event="ACCOUNT_UNLOCKED"
            else:
                con.execute("UPDATE users SET active=0 WHERE username=?",(username,))
                event="ACCOUNT_DISABLED"
            con.execute("UPDATE security_alerts SET status='Resolved',resolved_by=?,resolved_at=CURRENT_TIMESTAMP WHERE id=?",
                        (self.user["username"],alert_id)); con.commit()
        from security.audit_logger import log_action
        log_action(self.user,event,f"Admin action for {username}")
        self.alerts_page()

    def ledger_page(self):
        self.heading("Tamper-evident audit ledger","SHA-256 hash chain; educational hash-chained ledger, not decentralized blockchain")
        from security.ledger import verify_ledger
        ok,count=verify_ledger()
        tk.Label(self.content,text=f"Ledger entries: {count}",bg=BG,fg=NAVY,font=("Segoe UI",12,"bold")).pack(anchor="w")
        tk.Label(self.content,text=("LEDGER VERIFIED" if ok else f"TAMPERING DETECTED at entry {count}"),
                 bg=BG,fg=TEAL if ok else "#B91C1C",font=("Segoe UI",18,"bold")).pack(anchor="w",pady=12)
        ttk.Button(self.content,text="Verify again",command=self.ledger_page).pack(anchor="w")

    def sql_lab(self):
        self.heading("SQL Injection Demonstration Lab","Isolated local examples; the production login remains parameterized and protected")
        box=tk.Frame(self.content,bg="white",padx=16,pady=14); box.pack(fill="x")
        tk.Label(box,text="Test input (use only in this local teaching lab):",bg="white").pack(anchor="w")
        payload=ttk.Entry(box,width=48); payload.insert(0,"' OR '1'='1' --"); payload.pack(anchor="w",pady=8)
        out=tk.Label(box,text="Run the comparison to see why parameterized queries matter.",bg="white",fg=NAVY)
        out.pack(anchor="w",pady=8)
        def run():
            value=payload.get()
            # Vulnerable example is intentionally isolated and uses a disposable in-memory database.
            demo=__import__("sqlite3").connect(":memory:")
            demo.execute("CREATE TABLE demo_users(username TEXT,password TEXT)")
            demo.execute("INSERT INTO demo_users VALUES('teacher','correct-password')")
            vulnerable=f"SELECT * FROM demo_users WHERE username='{value}' AND password='wrong'"
            try: bypass=demo.execute(vulnerable).fetchone() is not None
            except Exception: bypass=False
            safe=demo.execute("SELECT * FROM demo_users WHERE username=? AND password=?", (value,"wrong")).fetchone()
            out.config(text=f"Unsafe string-built query: {'BYPASS POSSIBLE' if bypass else 'No bypass for this input'}\nProtected parameterized query: {'Unexpected match' if safe else 'REJECTED â€“ input treated as data'}",
                       fg="#B91C1C" if bypass else TEAL)
        ttk.Button(box,text="Run isolated comparison",command=run).pack(anchor="w")

    def prescription_page(self):
        self.heading("Digitally signed prescriptions","Doctor can sign prescriptions only for patients assigned to their appointments")
        form=tk.Frame(self.content,bg="white",padx=14,pady=12); form.pack(fill="x")
        tk.Label(form,text="Patient ID",bg="white").grid(row=0,column=0,padx=5)
        pid=ttk.Entry(form,width=10); pid.grid(row=0,column=1,padx=5)
        tk.Label(form,text="Prescription / medicines and dosage",bg="white").grid(row=0,column=2,padx=5)
        report=ttk.Entry(form,width=48); report.grid(row=0,column=3,padx=5)
        ttk.Button(form,text="Create signed prescription",command=lambda:self.create_prescription(pid.get(),report.get())).grid(row=0,column=4,padx=5)
        with connect() as con:
            rows=con.execute("SELECT pr.id,p.full_name,pr.version,pr.created_at FROM prescriptions pr JOIN patients p ON p.id=pr.patient_id JOIN doctors d ON d.id=pr.doctor_id WHERE d.user_id=? ORDER BY pr.id DESC",(self.user["id"],)).fetchall()
        tree=self.table(("id","full_name","version","created_at"),rows)
        ttk.Button(self.content,text="Verify selected prescription signature",
                   command=lambda:self.verify_prescription(tree)).pack(anchor="w",pady=8)

    def verify_prescription(self,tree):
        selected=tree.selection()
        if not selected:
            messagebox.showwarning("Select prescription","Choose a prescription first."); return
        prescription_id=int(tree.item(selected[0],"values")[0])
        with connect() as con:
            row=con.execute("""SELECT pr.*,p.full_name,d.name AS doctor_name FROM prescriptions pr
                JOIN patients p ON p.id=pr.patient_id JOIN doctors d ON d.id=pr.doctor_id
                WHERE pr.id=? AND d.user_id=?""",(prescription_id,self.user["id"])).fetchone()
        if not row:
            messagebox.showerror("Not authorized","You cannot verify another doctor's prescription."); return
        from security.prescription_signing import verify_payload
        valid=verify_payload(row["report_text"],row["signature"])
        messagebox.showinfo("Signature verification","VALID â€“ prescription content is authentic." if valid
                            else "INVALID â€“ signature verification failed.")

    def create_prescription(self,pid,text):
        try:
            pid=int(pid); text=text.strip()
            if not text: raise ValueError("Enter prescription details.")
            with connect() as con:
                doc=con.execute("SELECT id,name FROM doctors WHERE user_id=?",(self.user["id"],)).fetchone()
                assigned=con.execute("SELECT 1 FROM appointments WHERE patient_id=? AND doctor_id=?",(pid,doc["id"])).fetchone()
                if not assigned: raise PermissionError("You can prescribe only for your assigned patients.")
                patient=con.execute("SELECT full_name,email,phone FROM patients WHERE id=?",(pid,)).fetchone()
                if not patient: raise ValueError("Patient not found.")
                payload=f"patient_id={pid}|patient={patient['full_name']}|doctor_id={doc['id']}|doctor={doc['name']}|prescription={text}"
                from security.prescription_signing import sign_payload
                sig=sign_payload(payload)
                con.execute("INSERT INTO prescriptions(patient_id,doctor_id,report_text,signature) VALUES(?,?,?,?)",(pid,doc["id"],payload,sig))
                con.commit()
            from security.audit_logger import log_action
            log_action(self.user,"PRESCRIPTION_SIGNED",f"Signed prescription for patient ID {pid}")
            if messagebox.askyesno("Prescription saved","Digitally signed report saved.\n\nSend it to the patient's registered email and/or mobile now?"):
                try:
                    from security.report_pdf import create_patient_report_pdf
                    from security.delivery import send_patient_report

                    if not patient["email"]:
                        raise ValueError("Patient email is missing. Add an email address to this patient's record first.")

                    pdf_bytes = create_patient_report_pdf(
                        patient_name=patient["full_name"],
                        patient_id=pid,
                        doctor_name=doc["name"],
                        doctor_id=doc["id"],
                        prescription=text,
                        signature=sig,
                    )

                    send_patient_report(patient["email"], None, payload, sig, pdf_bytes)
                    log_action(self.user,"PRESCRIPTION_DELIVERED",f"Signed PDF report emailed for patient ID {pid}")
                    messagebox.showinfo("Email submitted","The signed PDF report was submitted to the patient's registered email. SMS was not used.")
                except Exception as delivery_error: messagebox.showerror("Report delivery failed",str(delivery_error))
            messagebox.showinfo("Success","Prescription digitally signed and saved.")
            self.prescription_page()
        except Exception as e: messagebox.showerror("Cannot create prescription",str(e))

    def logout(self):
        from security.audit_logger import log_action
        log_action(self.user,"LOGOUT","User signed out")
        self.user=None
        self.login_screen()

if __name__ == "__main__":
    initialize()
    root=tk.Tk()
    try:
        style=ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=("Segoe UI",10))
        style.configure("Treeview.Heading", font=("Segoe UI",10,"bold"))
        style.configure("TButton", font=("Segoe UI",10), padding=7)
    except Exception: pass
    CareSecureApp(root)
    root.mainloop()

