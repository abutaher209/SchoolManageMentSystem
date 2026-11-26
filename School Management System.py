import os
import sys
import csv
import shutil
import sqlite3
import hashlib
import webbrowser
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
# CONFIGURATION & THEME COLORS (100% BUILT-IN PYTHON LIBRARIES ONLY)
# ==============================================================================
DB_NAME = "school_management.db"
PHOTO_DIR = "student_photos"
ASSETS_DIR = "school_assets"
EXPORT_DIR = "exports"

for folder in [PHOTO_DIR, ASSETS_DIR, EXPORT_DIR]:
    os.makedirs(folder, exist_ok=True)

COLORS = {
    "bg_main": "#F1F5F9",
    "bg_card": "#FFFFFF",
    "sidebar": "#0F172A",
    "sidebar_hover": "#1E293B",
    "sidebar_active": "#2563EB",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#06B6D4",
    "purple": "#8B5CF6",
    "text_dark": "#0F172A",
    "text_muted": "#64748B",
    "border": "#CBD5E1"
}


# ==============================================================================
# BUILT-IN PHOTO HELPER (NO PIL REQUIRED)
# ==============================================================================
def create_demo_avatar_png(filepath, bg_color="#2563EB", fg_color="#FFFFFF"):
    temp_root = tk._default_root
    owns_root = False
    if temp_root is None:
        temp_root = tk.Tk()
        temp_root.withdraw()
        owns_root = True

    img = tk.PhotoImage(width=96, height=96)
    img.put(bg_color, to=(0, 0, 96, 96))
    img.put("#FFFFFF", to=(8, 8, 88, 88))
    img.put(bg_color, to=(12, 12, 84, 84))
    img.put(fg_color, to=(34, 22, 62, 48))
    img.put(fg_color, to=(22, 54, 74, 80))
    img.write(filepath, format="png")

    if owns_root:
        temp_root.destroy()


def load_tk_photo(path, max_size=110):
    if not path or not os.path.exists(path):
        return None
    try:
        raw = tk.PhotoImage(file=path)
        w, h = raw.width(), raw.height()
        scale = max(1, max(w // max_size, h // max_size))
        if scale > 1:
            return raw.subsample(scale, scale)
        return raw
    except tk.TclError:
        return None


# ==============================================================================
# DATABASE MANAGER + DEMO DATA SEEDER
# ==============================================================================
class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()
        self.seed_demo_data()

    def connect(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def init_db(self):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT 'System Administrator',
                email TEXT DEFAULT 'admin@school.edu',
                phone TEXT DEFAULT '01700000000'
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                school_name TEXT DEFAULT 'Modern Ideal School & College',
                address TEXT DEFAULT '123 Education Avenue, Dhaka',
                phone TEXT DEFAULT '+880 1700-000000',
                email TEXT DEFAULT 'info@modernideal.edu',
                logo_path TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT UNIQUE NOT NULL,
                sections TEXT DEFAULT 'A,B'
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                father_name TEXT,
                mother_name TEXT,
                dob TEXT,
                gender TEXT,
                phone TEXT,
                email TEXT,
                present_address TEXT,
                permanent_address TEXT,
                class_name TEXT,
                section TEXT,
                roll_number TEXT NOT NULL,
                admission_date TEXT,
                blood_group TEXT,
                guardian_phone TEXT,
                photo_path TEXT,
                status TEXT DEFAULT 'Active',
                UNIQUE(class_name, section, roll_number)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                subject TEXT,
                phone TEXT,
                email TEXT,
                address TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                section TEXT NOT NULL,
                att_date TEXT NOT NULL,
                status TEXT NOT NULL,
                late_minutes INTEGER DEFAULT 0,
                UNIQUE(student_id, att_date),
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)

        # Ensure late_minutes exists on existing databases
        att_cols = [r[1] for r in cur.execute("PRAGMA table_info(attendance)").fetchall()]
        if "late_minutes" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN late_minutes INTEGER DEFAULT 0")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT UNIQUE NOT NULL,
                exam_date TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT UNIQUE NOT NULL,
                full_marks REAL DEFAULT 100
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT NOT NULL,
                student_id TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                marks_obtained REAL NOT NULL,
                full_marks REAL DEFAULT 100,
                UNIQUE(exam_name, student_id, subject_name),
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT UNIQUE NOT NULL,
                student_id TEXT NOT NULL,
                fee_type TEXT NOT NULL,
                total_amount REAL NOT NULL,
                paid_amount REAL NOT NULL,
                due_amount REAL NOT NULL,
                status TEXT NOT NULL,
                payment_date TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)

        cur.execute("SELECT COUNT(*) FROM admin")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO admin (username, password_hash, full_name) VALUES (?, ?, ?)",
                ("admin", self.hash_password("admin123"), "Principal / Admin")
            )

        cur.execute("SELECT COUNT(*) FROM settings")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO settings (id, school_name) VALUES (1, 'Modern Ideal School & College')")

        cur.execute("SELECT COUNT(*) FROM classes")
        if cur.fetchone()[0] == 0:
            sample_classes = [
                ("Class 6", "A,B"),
                ("Class 7", "A,B"),
                ("Class 8", "A,B"),
                ("Class 9", "Science,Commerce,Arts"),
                ("Class 10", "Science,Commerce,Arts")
            ]
            for c in sample_classes:
                cur.execute("INSERT INTO classes (class_name, sections) VALUES (?, ?)", c)

        cur.execute("SELECT COUNT(*) FROM subjects")
        if cur.fetchone()[0] == 0:
            sample_subjects = [
                ("Bangla", 100),
                ("English", 100),
                ("Mathematics", 100),
                ("General Science", 100),
                ("ICT", 100)
            ]
            for s in sample_subjects:
                cur.execute("INSERT INTO subjects (subject_name, full_marks) VALUES (?, ?)", s)

        cur.execute("SELECT COUNT(*) FROM exams")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO exams (exam_name, exam_date) VALUES (?, ?)", ("Mid-Term Examination 2026", "2026-06-15"))
            cur.execute("INSERT INTO exams (exam_name, exam_date) VALUES (?, ?)", ("Final Examination 2026", "2026-11-20"))

        conn.commit()
        conn.close()

    def seed_demo_data(self):
        conn = self.connect()
        cur = conn.cursor()

        demo_teachers = [
            ("TCH-2026-01", "Md. Rafiqul Islam", "Mathematics", "01711223344", "rafiq.math@school.edu", "Mirpur-10, Dhaka"),
            ("TCH-2026-02", "Farhana Akter", "English", "01812345678", "farhana.eng@school.edu", "Dhanmondi-7, Dhaka"),
            ("TCH-2026-03", "Dr. Kamrul Hasan", "General Science", "01911445566", "kamrul.sci@school.edu", "Uttara Sector-4, Dhaka"),
            ("TCH-2026-04", "Nusrat Jahan", "ICT", "01615566778", "nusrat.ict@school.edu", "Mohammadpur, Dhaka"),
        ]
        for t in demo_teachers:
            cur.execute("INSERT OR IGNORE INTO teachers VALUES (?,?,?,?,?,?)", t)

        demo_students = [
            ("STU-2026-0001", "Arif Mahmud", "Abul Kalam", "Salma Begum", "2011-03-14", "Male", "01720001101", "arif.m@student.edu", "Mirpur-1, Dhaka", "Tangail Sadar", "Class 6", "A", "1", "2026-01-10", "O+", "01710001101", "Active", "#2563EB"),
            ("STU-2026-0002", "Tanjina Rahman", "Mizanur Rahman", "Rokeya Khatun", "2011-07-22", "Female", "01820001102", "tanjina.r@student.edu", "Dhanmondi-15, Dhaka", "Cumilla Sadar", "Class 6", "A", "2", "2026-01-11", "A+", "01810001102", "Active", "#8B5CF6"),
            ("STU-2026-0003", "Sabbir Hossain", "Shahidul Islam", "Nasrin Akter", "2010-05-09", "Male", "01920001103", "sabbir.h@student.edu", "Uttara-9, Dhaka", "Gazipur", "Class 6", "A", "3", "2026-01-12", "B+", "01910001103", "Active", "#0EA5E9"),
            ("STU-2026-0004", "Mehedi Hasan", "Zahidul Haque", "Parvin Sultana", "2012-11-18", "Male", "01520001104", "mehedi.h@student.edu", "Jatrabari, Dhaka", "Narayanganj", "Class 8", "A", "1", "2026-01-15", "AB+", "01510001104", "Active", "#10B981"),
            ("STU-2026-0005", "Lamia Tabassum", "Tariq Aziz", "Shirin Akter", "2013-02-27", "Female", "01620001105", "lamia.t@student.edu", "Banani, Dhaka", "Sylhet", "Class 7", "A", "1", "2026-01-18", "O-", "01610001105", "Active", "#EC4899"),
            ("STU-2026-0006", "Tanvir Ahmed", "Moniruzzaman", "Hasina Begum", "2010-09-04", "Male", "01720001106", "tanvir.a@student.edu", "Shyamoli, Dhaka", "Rajshahi", "Class 9", "Science", "1", "2026-01-20", "A-", "01710001106", "Inactive", "#F59E0B"),
        ]

        for s in demo_students:
            sid, name, fname, mname, dob, gender, phone, email, pres, perm, cls_n, sec, roll, adm_d, bg, g_phone, status, avatar_col = s
            photo_file = os.path.join(PHOTO_DIR, f"{sid}.png")
            if not os.path.exists(photo_file):
                create_demo_avatar_png(photo_file, bg_color=avatar_col)
            cur.execute("""
                INSERT OR IGNORE INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (sid, name, fname, mname, dob, gender, phone, email, pres, perm, cls_n, sec, roll, adm_d, bg, g_phone, photo_file, status))

        today_str = date.today().isoformat()
        demo_att = [
            ("STU-2026-0001", "Class 6", "A", today_str, "Present", 0),
            ("STU-2026-0002", "Class 6", "A", today_str, "Present", 0),
            ("STU-2026-0003", "Class 6", "A", today_str, "Late", 15),
            ("STU-2026-0004", "Class 8", "A", today_str, "Present", 0),
            ("STU-2026-0005", "Class 7", "A", today_str, "Leave", 0),
        ]
        for att in demo_att:
            cur.execute(
                "INSERT OR IGNORE INTO attendance (student_id, class_name, section, att_date, status, late_minutes) VALUES (?,?,?,?,?,?)",
                att
            )

        demo_marks = [
            ("Mid-Term Examination 2026", "STU-2026-0001", "Bangla", 84, 100),
            ("Mid-Term Examination 2026", "STU-2026-0001", "English", 88, 100),
            ("Mid-Term Examination 2026", "STU-2026-0001", "Mathematics", 92, 100),
            ("Mid-Term Examination 2026", "STU-2026-0002", "Bangla", 79, 100),
            ("Mid-Term Examination 2026", "STU-2026-0002", "English", 82, 100),
            ("Mid-Term Examination 2026", "STU-2026-0002", "Mathematics", 76, 100),
            ("Mid-Term Examination 2026", "STU-2026-0003", "Bangla", 72, 100),
            ("Mid-Term Examination 2026", "STU-2026-0003", "English", 68, 100),
            ("Mid-Term Examination 2026", "STU-2026-0003", "Mathematics", 81, 100),
        ]
        for mk in demo_marks:
            cur.execute("INSERT OR IGNORE INTO marks (exam_name, student_id, subject_name, marks_obtained, full_marks) VALUES (?,?,?,?,?)", mk)

        demo_fees = [
            ("RCP-20260001", "STU-2026-0001", "Monthly Fees", 1500.0, 1500.0, 0.0, "Paid", today_str),
            ("RCP-20260002", "STU-2026-0002", "Monthly Fees", 1500.0, 1000.0, 500.0, "Unpaid / Partial", today_str),
            ("RCP-20260003", "STU-2026-0003", "Exam Fees", 1200.0, 1200.0, 0.0, "Paid", today_str),
        ]
        for f in demo_fees:
            cur.execute("INSERT OR IGNORE INTO fees (receipt_no, student_id, fee_type, total_amount, paid_amount, due_amount, status, payment_date) VALUES (?,?,?,?,?,?,?,?)", f)

        conn.commit()
        conn.close()


# ==============================================================================
# UTILITY FUNCTIONS (CSV, PRINTABLE HTML, GPA)
# ==============================================================================
def calculate_grade_gpa(percentage):
    if percentage >= 80:
        return "A+", 5.00
    elif percentage >= 70:
        return "A", 4.00
    elif percentage >= 60:
        return "A-", 3.50
    elif percentage >= 50:
        return "B", 3.00
    elif percentage >= 40:
        return "C", 2.00
    elif percentage >= 33:
        return "D", 1.00
    else:
        return "F", 0.00


def export_to_csv(filename, headers, rows):
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return os.path.abspath(filepath)


def export_printable_document(filename, title, subtitle, headers, rows):
    base_name = os.path.splitext(filename)[0]
    html_path = os.path.join(EXPORT_DIR, f"{base_name}.html")
    th_html = "".join(f"<th>{h}</th>" for h in headers)
    tr_html = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 28px; color: #0F172A; }}
    .header {{ border-bottom: 3px solid #2563EB; padding-bottom: 10px; margin-bottom: 18px; }}
    h1 {{ margin: 0; font-size: 22px; color: #2563EB; }}
    p {{ margin: 6px 0 0; color: #475569; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #CBD5E1; padding: 9px 10px; text-align: center; font-size: 13px; }}
    th {{ background: #2563EB; color: #FFFFFF; font-weight: 600; }}
    tr:nth-child(even) {{ background: #F8FAFC; }}
    .print-btn {{ margin-bottom: 14px; padding: 8px 16px; background: #10B981; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }}
    @media print {{ .print-btn {{ display: none; }} }}
</style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
    <div class="header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    <table>
        <thead><tr>{th_html}</tr></thead>
        <tbody>{tr_html}</tbody>
    </table>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return os.path.abspath(html_path)


def open_file_for_print(filepath):
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform == "darwin":
            os.system(f"open '{filepath}'")
        else:
            webbrowser.open(f"file://{filepath}")
    except Exception as e:
        messagebox.showinfo("File Saved", f"Document saved at:\n{filepath}\n({e})")


# ==============================================================================
# LOGIN WINDOW
# ==============================================================================
class LoginWindow:
    def __init__(self, root, db, on_login_success):
        self.root = root
        self.db = db
        self.on_login_success = on_login_success
        self.root.title("Admin Login - Student Management System")
        self.root.geometry("900x560")
        self.root.minsize(750, 500)
        self.root.configure(bg=COLORS["bg_main"])
        self.build_ui()

    def build_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        container = tk.Frame(self.root, bg=COLORS["bg_main"])
        container.pack(fill="both", expand=True)

        left_panel = tk.Frame(container, bg=COLORS["sidebar"], width=380)
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        conn = self.db.connect()
        school_name = conn.execute("SELECT school_name FROM settings WHERE id=1").fetchone()[0]
        conn.close()

        tk.Label(left_panel, text="🎓", font=("Segoe UI Emoji", 54), bg=COLORS["sidebar"], fg="white").pack(pady=(90, 10))
        tk.Label(left_panel, text=school_name, font=("Segoe UI", 16, "bold"), bg=COLORS["sidebar"], fg="white", wraplength=320, justify="center").pack(pady=5)
        tk.Label(left_panel, text="Advanced Student & Academic\nManagement System", font=("Segoe UI", 11), bg=COLORS["sidebar"], fg="#94A3B8", justify="center").pack(pady=10)
        tk.Label(left_panel, text="Zero External Plugin • SQLite Powered", font=("Segoe UI", 9, "italic"), bg=COLORS["sidebar"], fg=COLORS["info"]).pack(side="bottom", pady=30)

        right_panel = tk.Frame(container, bg=COLORS["bg_main"])
        right_panel.pack(side="right", fill="both", expand=True)

        card = tk.Frame(right_panel, bg=COLORS["bg_card"], padx=40, pady=40, highlightbackground=COLORS["border"], highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=400)

        tk.Label(card, text="Admin Login", font=("Segoe UI", 22, "bold"), bg=COLORS["bg_card"], fg=COLORS["text_dark"]).pack(anchor="w")
        tk.Label(card, text="Sign in to access the administration dashboard", font=("Segoe UI", 10), bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(anchor="w", pady=(2, 25))

        tk.Label(card, text="Username", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_card"], fg=COLORS["text_dark"]).pack(anchor="w")
        self.username_var = tk.StringVar(value="admin")
        ent_user = ttk.Entry(card, textvariable=self.username_var, font=("Segoe UI", 11))
        ent_user.pack(fill="x", ipady=6, pady=(5, 15))

        tk.Label(card, text="Password", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_card"], fg=COLORS["text_dark"]).pack(anchor="w")
        self.password_var = tk.StringVar()
        ent_pass = ttk.Entry(card, textvariable=self.password_var, show="●", font=("Segoe UI", 11))
        ent_pass.pack(fill="x", ipady=6, pady=(5, 10))
        ent_pass.bind("<Return>", lambda e: self.handle_login())

        self.show_pass_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card, text="Show Password", variable=self.show_pass_var,
            bg=COLORS["bg_card"], activebackground=COLORS["bg_card"],
            command=lambda: ent_pass.config(show="" if self.show_pass_var.get() else "●")
        ).pack(anchor="w", pady=(0, 20))

        btn_login = tk.Button(
            card, text="LOGIN TO DASHBOARD", font=("Segoe UI", 11, "bold"),
            bg=COLORS["primary"], fg="white", activebackground=COLORS["primary_dark"],
            activeforeground="white", bd=0, cursor="hand2", command=self.handle_login
        )
        btn_login.pack(fill="x", ipady=10)

        tk.Label(card, text="Default: admin / admin123", font=("Segoe UI", 9), bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(pady=(15, 0))

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Validation Error", "Please enter both Username and Password.")
            return

        conn = self.db.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, full_name FROM admin WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()

        if row and row[2] == self.db.hash_password(password):
            self.on_login_success({"id": row[0], "username": row[1], "full_name": row[3]})
        else:
            messagebox.showerror("Authentication Failed", "Invalid Username or Password! Please try again.")


# ==============================================================================
# MAIN APPLICATION DASHBOARD
# ==============================================================================
class StudentManagementApp:
    def __init__(self, root, db, admin_user, on_logout):
        self.root = root
        self.db = db
        self.admin_user = admin_user
        self.on_logout = on_logout

        self.root.title("Advanced Student Management System")
        self.root.geometry("1320x780")
        self.root.minsize(1100, 680)
        self.root.configure(bg=COLORS["bg_main"])

        self.configure_styles()
        self.nav_buttons = {}
        self.build_layout()
        self.update_clock()
        self.switch_page("dashboard")

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", foreground=COLORS["text_dark"], rowheight=30, fieldbackground="white", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#E2E8F0", foreground=COLORS["text_dark"], font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", COLORS["primary"])], foreground=[("selected", "white")])
        style.configure("TCombobox", padding=4)
        style.configure("TEntry", padding=4)

    def build_layout(self):
        for w in self.root.winfo_children():
            w.destroy()

        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand_frame = tk.Frame(self.sidebar, bg="#0B1120", pady=18, padx=15)
        brand_frame.pack(fill="x")
        tk.Label(brand_frame, text="🎓 EDU-PRO SMS", font=("Segoe UI", 14, "bold"), bg="#0B1120", fg="white").pack(anchor="w")
        tk.Label(brand_frame, text="Management Portal", font=("Segoe UI", 9), bg="#0B1120", fg="#94A3B8").pack(anchor="w")

        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("students", "👨‍🎓  Student Management"),
            ("teachers", "👩‍🏫  Teacher Management"),
            ("classes", "🏫  Class & Section"),
            ("attendance", "📅  Attendance"),
            ("exams", "📝  Exam & Results"),
            ("fees", "💳  Fees Management"),
            ("reports", "📑  Reports & Export"),
            ("settings", "⚙️  Settings & Backup"),
        ]

        nav_container = tk.Frame(self.sidebar, bg=COLORS["sidebar"], pady=10)
        nav_container.pack(fill="both", expand=True)

        for key, label in nav_items:
            btn = tk.Button(
                nav_container, text=label, font=("Segoe UI", 10, "bold"),
                bg=COLORS["sidebar"], fg="#CBD5E1", activebackground=COLORS["sidebar_hover"],
                activeforeground="white", bd=0, anchor="w", padx=20, pady=11,
                cursor="hand2", command=lambda k=key: self.switch_page(k)
            )
            btn.pack(fill="x", pady=1)
            self.nav_buttons[key] = btn

        btn_logout = tk.Button(
            self.sidebar, text="🚪  Logout", font=("Segoe UI", 10, "bold"),
            bg="#7F1D1D", fg="white", activebackground="#991B1B", activeforeground="white",
            bd=0, anchor="w", padx=20, pady=12, cursor="hand2", command=self.confirm_logout
        )
        btn_logout.pack(fill="x", side="bottom")

        right_area = tk.Frame(self.root, bg=COLORS["bg_main"])
        right_area.pack(side="right", fill="both", expand=True)

        self.topbar = tk.Frame(right_area, bg="white", height=64, highlightbackground=COLORS["border"], highlightthickness=1)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        self.lbl_school_title = tk.Label(self.topbar, text="", font=("Segoe UI", 14, "bold"), bg="white", fg=COLORS["text_dark"])
        self.lbl_school_title.pack(side="left", padx=20)
        self.refresh_school_header()

        right_top_info = tk.Frame(self.topbar, bg="white")
        right_top_info.pack(side="right", padx=20)

        self.lbl_clock = tk.Label(right_top_info, text="", font=("Segoe UI", 9, "bold"), bg="white", fg=COLORS["primary"])
        self.lbl_clock.pack(anchor="e")
        tk.Label(right_top_info, text=f"👤 {self.admin_user['full_name']} ({self.admin_user['username']})", font=("Segoe UI", 9), bg="white", fg=COLORS["text_muted"]).pack(anchor="e")

        self.content_frame = tk.Frame(right_area, bg=COLORS["bg_main"], padx=20, pady=15)
        self.content_frame.pack(fill="both", expand=True)

    def refresh_school_header(self):
        conn = self.db.connect()
        row = conn.execute("SELECT school_name FROM settings WHERE id=1").fetchone()
        conn.close()
        self.lbl_school_title.config(text=f"🏛️  {row[0]}" if row else "Student Management System")

    def update_clock(self):
        now_str = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        if self.lbl_clock.winfo_exists():
            self.lbl_clock.config(text=now_str)
            self.root.after(1000, self.update_clock)

    def confirm_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.on_logout()

    def switch_page(self, page_key):
        for k, btn in self.nav_buttons.items():
            if k == page_key:
                btn.config(bg=COLORS["sidebar_active"], fg="white")
            else:
                btn.config(bg=COLORS["sidebar"], fg="#CBD5E1")

        for w in self.content_frame.winfo_children():
            w.destroy()

        pages = {
            "dashboard": self.render_dashboard,
            "students": self.render_students,
            "teachers": self.render_teachers,
            "classes": self.render_classes,
            "attendance": self.render_attendance,
            "exams": self.render_exams,
            "fees": self.render_fees,
            "reports": self.render_reports,
            "settings": self.render_settings,
        }
        pages[page_key]()

    # ==========================================================================
    # DASHBOARD
    # ==========================================================================
    def render_dashboard(self):
        tk.Label(self.content_frame, text="Dashboard Overview", font=("Segoe UI", 18, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 15))

        conn = self.db.connect()
        cur = conn.cursor()
        total_students = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        male_students = cur.execute("SELECT COUNT(*) FROM students WHERE gender='Male'").fetchone()[0]
        female_students = cur.execute("SELECT COUNT(*) FROM students WHERE gender='Female'").fetchone()[0]
        total_teachers = cur.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
        total_classes = cur.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        active_students = cur.execute("SELECT COUNT(*) FROM students WHERE status='Active'").fetchone()[0]
        conn.close()

        cards_data = [
            ("Total Students", total_students, "👨‍🎓", COLORS["primary"]),
            ("Total Male Students", male_students, "👦", COLORS["info"]),
            ("Total Female Students", female_students, "👧", COLORS["purple"]),
            ("Total Teachers", total_teachers, "👩‍🏫", COLORS["warning"]),
            ("Total Classes", total_classes, "🏫", "#EC4899"),
            ("Total Active Students", active_students, "✅", COLORS["success"]),
        ]

        grid_frame = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        grid_frame.pack(fill="x")

        for i in range(3):
            grid_frame.columnconfigure(i, weight=1)

        for idx, (title, value, icon, accent) in enumerate(cards_data):
            r, c = divmod(idx, 3)
            card = tk.Frame(grid_frame, bg="white", padx=22, pady=20, highlightbackground=COLORS["border"], highlightthickness=1)
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

            top_strip = tk.Frame(card, bg=accent, height=4)
            top_strip.pack(fill="x", side="top", pady=(0, 12))

            row_f = tk.Frame(card, bg="white")
            row_f.pack(fill="x")

            text_f = tk.Frame(row_f, bg="white")
            text_f.pack(side="left")
            tk.Label(text_f, text=title, font=("Segoe UI", 11, "bold"), bg="white", fg=COLORS["text_muted"]).pack(anchor="w")
            tk.Label(text_f, text=str(value), font=("Segoe UI", 28, "bold"), bg="white", fg=COLORS["text_dark"]).pack(anchor="w", pady=(4, 0))

            tk.Label(row_f, text=icon, font=("Segoe UI Emoji", 34), bg="white").pack(side="right")

        bottom_frame = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        bottom_frame.pack(fill="both", expand=True, pady=(15, 0))

        recent_card = tk.Frame(bottom_frame, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        recent_card.pack(side="left", fill="both", expand=True, padx=(10, 10))

        tk.Label(recent_card, text="🆕 Recently Admitted Students", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 10))

        cols = ("ID", "Name", "Class", "Section", "Roll", "Phone")
        tree = ttk.Treeview(recent_card, columns=cols, show="headings", height=8)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")
        tree.pack(fill="both", expand=True)

        conn = self.db.connect()
        for row in conn.execute("SELECT student_id, full_name, class_name, section, roll_number, phone FROM students ORDER BY rowid DESC LIMIT 10"):
            tree.insert("", "end", values=row)
        conn.close()

        quick_card = tk.Frame(bottom_frame, bg="white", padx=18, pady=15, width=280, highlightbackground=COLORS["border"], highlightthickness=1)
        quick_card.pack(side="right", fill="y", padx=(0, 10))
        quick_card.pack_propagate(False)

        tk.Label(quick_card, text="⚡ Quick Actions", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        shortcuts = [
            ("+ Register New Student", COLORS["primary"], lambda: self.switch_page("students")),
            ("📅 Take Today's Attendance", COLORS["success"], lambda: self.switch_page("attendance")),
            ("📝 Enter Exam Marks", COLORS["purple"], lambda: self.switch_page("exams")),
            ("💳 Collect Student Fees", COLORS["warning"], lambda: self.switch_page("fees")),
            ("📑 Generate Reports", COLORS["info"], lambda: self.switch_page("reports")),
        ]
        for text, color, cmd in shortcuts:
            tk.Button(quick_card, text=text, bg=color, fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", pady=9, command=cmd).pack(fill="x", pady=5)

    # ==========================================================================
    # STUDENT MANAGEMENT
    # ==========================================================================
    def render_students(self):
        header_f = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        header_f.pack(fill="x", pady=(0, 10))
        tk.Label(header_f, text="Student Management & Directory", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(side="left")

        btn_bar = tk.Frame(header_f, bg=COLORS["bg_main"])
        btn_bar.pack(side="right")
        tk.Button(btn_bar, text="➕ Add Student", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=7, cursor="hand2", command=lambda: self.open_student_form()).pack(side="left", padx=4)
        tk.Button(btn_bar, text="👁️ View Profile", bg=COLORS["info"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=7, cursor="hand2", command=self.view_selected_student_profile).pack(side="left", padx=4)
        tk.Button(btn_bar, text="✏️ Edit", bg=COLORS["warning"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=7, cursor="hand2", command=self.edit_selected_student).pack(side="left", padx=4)
        tk.Button(btn_bar, text="🗑️ Delete", bg=COLORS["danger"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=7, cursor="hand2", command=self.delete_selected_student).pack(side="left", padx=4)

        filter_card = tk.Frame(self.content_frame, bg="white", padx=12, pady=10, highlightbackground=COLORS["border"], highlightthickness=1)
        filter_card.pack(fill="x", pady=(0, 10))

        tk.Label(filter_card, text="Search:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(0, 5))
        self.stu_search_var = tk.StringVar()
        ent_search = ttk.Entry(filter_card, textvariable=self.stu_search_var, width=28)
        ent_search.pack(side="left", padx=5)
        ent_search.bind("<KeyRelease>", lambda e: self.load_students_table())

        tk.Label(filter_card, text="Filter By:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(10, 5))
        self.stu_filter_by = ttk.Combobox(filter_card, values=["All Fields", "Name", "Student ID", "Roll Number", "Class", "Section", "Phone Number"], state="readonly", width=15)
        self.stu_filter_by.set("All Fields")
        self.stu_filter_by.pack(side="left", padx=5)
        self.stu_filter_by.bind("<<ComboboxSelected>>", lambda e: self.load_students_table())

        tk.Label(filter_card, text="Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(10, 5))
        conn = self.db.connect()
        classes = ["All"] + [r[0] for r in conn.execute("SELECT class_name FROM classes").fetchall()]
        conn.close()
        self.stu_class_filter = ttk.Combobox(filter_card, values=classes, state="readonly", width=14)
        self.stu_class_filter.set("All")
        self.stu_class_filter.pack(side="left", padx=5)
        self.stu_class_filter.bind("<<ComboboxSelected>>", lambda e: self.load_students_table())

        tk.Button(filter_card, text="Reset", bg="#E2E8F0", fg=COLORS["text_dark"], font=("Segoe UI", 9), bd=0, padx=10, pady=4, command=self.reset_student_filters).pack(side="left", padx=10)

        table_card = tk.Frame(self.content_frame, bg="white", padx=10, pady=10, highlightbackground=COLORS["border"], highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        cols = ("Student ID", "Full Name", "Gender", "Class", "Section", "Roll", "Phone", "Guardian Phone", "Blood", "Status")
        self.stu_tree = ttk.Treeview(table_card, columns=cols, show="headings")
        widths = [100, 170, 75, 90, 75, 65, 110, 115, 65, 75]
        for col, w in zip(cols, widths):
            self.stu_tree.heading(col, text=col)
            self.stu_tree.column(col, width=w, anchor="center")

        sb_y = ttk.Scrollbar(table_card, orient="vertical", command=self.stu_tree.yview)
        self.stu_tree.configure(yscrollcommand=sb_y.set)
        self.stu_tree.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")
        self.stu_tree.bind("<Double-1>", lambda e: self.view_selected_student_profile())

        self.load_students_table()

    def reset_student_filters(self):
        self.stu_search_var.set("")
        self.stu_filter_by.set("All Fields")
        self.stu_class_filter.set("All")
        self.load_students_table()

    def load_students_table(self):
        for item in self.stu_tree.get_children():
            self.stu_tree.delete(item)

        keyword = self.stu_search_var.get().strip()
        field = self.stu_filter_by.get()
        cls_filter = self.stu_class_filter.get()

        query = "SELECT student_id, full_name, gender, class_name, section, roll_number, phone, guardian_phone, blood_group, status FROM students WHERE 1=1"
        params = []

        if cls_filter != "All":
            query += " AND class_name = ?"
            params.append(cls_filter)

        if keyword:
            like = f"%{keyword}%"
            field_map = {
                "Name": "full_name LIKE ?",
                "Student ID": "student_id LIKE ?",
                "Roll Number": "roll_number LIKE ?",
                "Class": "class_name LIKE ?",
                "Section": "section LIKE ?",
                "Phone Number": "(phone LIKE ? OR guardian_phone LIKE ?)"
            }
            if field in field_map:
                query += f" AND {field_map[field]}"
                if field == "Phone Number":
                    params.extend([like, like])
                else:
                    params.append(like)
            else:
                query += " AND (student_id LIKE ? OR full_name LIKE ? OR roll_number LIKE ? OR class_name LIKE ? OR section LIKE ? OR phone LIKE ?)"
                params.extend([like] * 6)

        conn = self.db.connect()
        for row in conn.execute(query + " ORDER BY class_name, CAST(roll_number AS INTEGER)", params):
            self.stu_tree.insert("", "end", values=row)
        conn.close()

    def generate_next_student_id(self):
        conn = self.db.connect()
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] + 1
        while True:
            sid = f"STU-{datetime.now().year}-{count:04d}"
            exists = conn.execute("SELECT 1 FROM students WHERE student_id=?", (sid,)).fetchone()
            if not exists:
                conn.close()
                return sid
            count += 1

    def open_student_form(self, student_data=None):
        win = tk.Toplevel(self.root)
        win.title("Edit Student" if student_data else "Add New Student")
        win.geometry("820x660")
        win.configure(bg="white")
        win.grab_set()

        tk.Label(win, text="✏️ Update Student Information" if student_data else "➕ Register New Student", font=("Segoe UI", 15, "bold"), bg="white", fg=COLORS["primary"]).pack(pady=12)

        main_f = tk.Frame(win, bg="white", padx=25)
        main_f.pack(fill="both", expand=True)

        conn = self.db.connect()
        class_rows = conn.execute("SELECT class_name, sections FROM classes").fetchall()
        conn.close()
        class_dict = {r[0]: [s.strip() for s in r[1].split(",") if s.strip()] for r in class_rows}
        class_list = list(class_dict.keys())

        vars_map = {
            "student_id": tk.StringVar(value=student_data[0] if student_data else self.generate_next_student_id()),
            "full_name": tk.StringVar(value=student_data[1] if student_data else ""),
            "father_name": tk.StringVar(value=student_data[2] if student_data else ""),
            "mother_name": tk.StringVar(value=student_data[3] if student_data else ""),
            "dob": tk.StringVar(value=student_data[4] if student_data else "2010-01-01"),
            "gender": tk.StringVar(value=student_data[5] if student_data else "Male"),
            "phone": tk.StringVar(value=student_data[6] if student_data else ""),
            "email": tk.StringVar(value=student_data[7] if student_data else ""),
            "present_address": tk.StringVar(value=student_data[8] if student_data else ""),
            "permanent_address": tk.StringVar(value=student_data[9] if student_data else ""),
            "class_name": tk.StringVar(value=student_data[10] if student_data else (class_list[0] if class_list else "")),
            "section": tk.StringVar(value=student_data[11] if student_data else "A"),
            "roll_number": tk.StringVar(value=student_data[12] if student_data else ""),
            "admission_date": tk.StringVar(value=student_data[13] if student_data else date.today().isoformat()),
            "blood_group": tk.StringVar(value=student_data[14] if student_data else "O+"),
            "guardian_phone": tk.StringVar(value=student_data[15] if student_data else ""),
            "status": tk.StringVar(value=student_data[17] if student_data else "Active"),
        }
        photo_state = {"path": student_data[16] if student_data else ""}

        form_grid = tk.Frame(main_f, bg="white")
        form_grid.pack(side="left", fill="both", expand=True)

        fields = [
            ("Student ID *", "student_id", "entry"),
            ("Full Name *", "full_name", "entry"),
            ("Father's Name", "father_name", "entry"),
            ("Mother's Name", "mother_name", "entry"),
            ("Date of Birth (YYYY-MM-DD)", "dob", "entry"),
            ("Gender", "gender", ["Male", "Female", "Other"]),
            ("Student Phone", "phone", "entry"),
            ("Email Address", "email", "entry"),
            ("Present Address", "present_address", "entry"),
            ("Permanent Address", "permanent_address", "entry"),
            ("Class *", "class_name", class_list),
            ("Section *", "section", class_dict.get(vars_map["class_name"].get(), ["A", "B"])),
            ("Roll Number *", "roll_number", "entry"),
            ("Admission Date", "admission_date", "entry"),
            ("Blood Group", "blood_group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
            ("Guardian Phone *", "guardian_phone", "entry"),
            ("Status", "status", ["Active", "Inactive"]),
        ]

        widgets = {}
        for idx, (label, key, ftype) in enumerate(fields):
            r, c = divmod(idx, 2)
            cell = tk.Frame(form_grid, bg="white", padx=6, pady=4)
            cell.grid(row=r, column=c, sticky="ew")
            tk.Label(cell, text=label, font=("Segoe UI", 8, "bold"), bg="white", fg=COLORS["text_dark"]).pack(anchor="w")
            if ftype == "entry":
                ent = ttk.Entry(cell, textvariable=vars_map[key], width=28)
                if key == "student_id" and student_data:
                    ent.config(state="readonly")
                ent.pack(fill="x")
                widgets[key] = ent
            else:
                cb = ttk.Combobox(cell, textvariable=vars_map[key], values=ftype, state="readonly", width=26)
                cb.pack(fill="x")
                widgets[key] = cb

        def on_class_change(event=None):
            secs = class_dict.get(vars_map["class_name"].get(), ["A", "B"])
            widgets["section"].config(values=secs)
            if secs:
                vars_map["section"].set(secs[0])
            if not student_data:
                conn = self.db.connect()
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM students WHERE class_name=? AND section=?",
                    (vars_map["class_name"].get(), vars_map["section"].get())
                ).fetchone()[0]
                conn.close()
                vars_map["roll_number"].set(str(cnt + 1))

        widgets["class_name"].bind("<<ComboboxSelected>>", on_class_change)
        if not student_data and not vars_map["roll_number"].get():
            on_class_change()

        photo_box = tk.Frame(main_f, bg="#F8FAFC", width=200, padx=12, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        photo_box.pack(side="right", fill="y", padx=(15, 0))
        photo_box.pack_propagate(False)

        tk.Label(photo_box, text="Student Photo", font=("Segoe UI", 10, "bold"), bg="#F8FAFC").pack(pady=(0, 8))
        lbl_preview = tk.Label(photo_box, text="No Photo", bg="#E2E8F0", width=16, height=7)
        lbl_preview.pack(pady=5)

        def render_preview(path):
            tk_img = load_tk_photo(path, max_size=120)
            if tk_img:
                lbl_preview.config(image=tk_img, text="", width=110, height=110)
                lbl_preview.image = tk_img
            else:
                lbl_preview.config(image="", text="No Photo", width=16, height=7)

        render_preview(photo_state["path"])

        def choose_photo():
            file = filedialog.askopenfilename(title="Select Student Photo", filetypes=[("Image Files", "*.png *.gif")])
            if file:
                ext = os.path.splitext(file)[1]
                dest = os.path.join(PHOTO_DIR, f"{vars_map['student_id'].get()}{ext}")
                shutil.copy(file, dest)
                photo_state["path"] = dest
                render_preview(dest)

        tk.Button(photo_box, text="📷 Upload Photo", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=6, cursor="hand2", command=choose_photo).pack(fill="x", pady=10)

        def save_student():
            sid = vars_map["student_id"].get().strip()
            name = vars_map["full_name"].get().strip()
            cls_n = vars_map["class_name"].get().strip()
            sec = vars_map["section"].get().strip()
            roll = vars_map["roll_number"].get().strip()

            if not sid or not name or not cls_n or not roll:
                messagebox.showerror("Validation Error", "Student ID, Full Name, Class, and Roll Number are required!", parent=win)
                return

            conn = self.db.connect()
            cur = conn.cursor()
            try:
                if student_data:
                    cur.execute("""
                        UPDATE students SET full_name=?, father_name=?, mother_name=?, dob=?, gender=?,
                        phone=?, email=?, present_address=?, permanent_address=?, class_name=?, section=?,
                        roll_number=?, admission_date=?, blood_group=?, guardian_phone=?, photo_path=?, status=?
                        WHERE student_id=?
                    """, (
                        name, vars_map["father_name"].get(), vars_map["mother_name"].get(), vars_map["dob"].get(),
                        vars_map["gender"].get(), vars_map["phone"].get(), vars_map["email"].get(),
                        vars_map["present_address"].get(), vars_map["permanent_address"].get(), cls_n, sec,
                        roll, vars_map["admission_date"].get(), vars_map["blood_group"].get(),
                        vars_map["guardian_phone"].get(), photo_state["path"], vars_map["status"].get(), sid
                    ))
                else:
                    cur.execute(
                        "INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            sid, name, vars_map["father_name"].get(), vars_map["mother_name"].get(), vars_map["dob"].get(),
                            vars_map["gender"].get(), vars_map["phone"].get(), vars_map["email"].get(),
                            vars_map["present_address"].get(), vars_map["permanent_address"].get(), cls_n, sec,
                            roll, vars_map["admission_date"].get(), vars_map["blood_group"].get(),
                            vars_map["guardian_phone"].get(), photo_state["path"], vars_map["status"].get()
                        )
                    )
                conn.commit()
                messagebox.showinfo("Success", "Student record saved successfully!", parent=win)
                win.destroy()
                self.load_students_table()
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate Entry", "Student ID or Roll Number in this Class & Section already exists!", parent=win)
            finally:
                conn.close()

        tk.Button(win, text="💾 SAVE STUDENT RECORD", bg=COLORS["success"], fg="white", font=("Segoe UI", 11, "bold"), bd=0, pady=10, cursor="hand2", command=save_student).pack(fill="x", padx=25, pady=15)

    def get_selected_student_id(self):
        sel = self.stu_tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a student from the table first.")
            return None
        return self.stu_tree.item(sel[0])["values"][0]

    def edit_selected_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            return
        conn = self.db.connect()
        row = conn.execute("SELECT * FROM students WHERE student_id=?", (sid,)).fetchone()
        conn.close()
        if row:
            self.open_student_form(row)

    def delete_selected_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            return
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete Student '{sid}'?\nAll linked attendance, marks, and fee records will also be removed."):
            conn = self.db.connect()
            conn.execute("DELETE FROM students WHERE student_id=?", (sid,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", "Student record deleted successfully.")
            self.load_students_table()

    def view_selected_student_profile(self):
        sid = self.get_selected_student_id()
        if not sid:
            return
        conn = self.db.connect()
        s = conn.execute("SELECT * FROM students WHERE student_id=?", (sid,)).fetchone()
        conn.close()
        if not s:
            return

        win = tk.Toplevel(self.root)
        win.title(f"Student Profile - {s[1]}")
        win.geometry("680x560")
        win.configure(bg="white")

        banner = tk.Frame(win, bg=COLORS["primary"], pady=15, padx=20)
        banner.pack(fill="x")
        tk.Label(banner, text="STUDENT ID CARD & PROFILE", font=("Segoe UI", 14, "bold"), bg=COLORS["primary"], fg="white").pack(side="left")

        body = tk.Frame(win, bg="white", padx=25, pady=20)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="white")
        left.pack(side="left", anchor="n", padx=(0, 20))
        tk_img = load_tk_photo(s[16], max_size=120)
        if tk_img:
            lbl_img = tk.Label(left, image=tk_img, bg="#E2E8F0")
            lbl_img.image = tk_img
        else:
            lbl_img = tk.Label(left, text="No Photo", bg="#E2E8F0", width=16, height=7)
        lbl_img.pack()

        tk.Label(left, text=s[0], font=("Segoe UI", 11, "bold"), bg="white", fg=COLORS["primary"]).pack(pady=(8, 2))
        tk.Label(left, text=f"Status: {s[17]}", font=("Segoe UI", 9, "bold"), bg="#DCFCE7" if s[17] == "Active" else "#FEE2E2", fg="#166534", padx=8, pady=2).pack()

        right = tk.Frame(body, bg="white")
        right.pack(side="left", fill="both", expand=True)
        details = [
            ("Full Name", s[1]),
            ("Class & Section", f"{s[10]} (Section: {s[11]})"),
            ("Roll Number", s[12]),
            ("Father's Name", s[2]),
            ("Mother's Name", s[3]),
            ("Date of Birth", s[4]),
            ("Gender / Blood", f"{s[5]}  |  Blood Group: {s[14]}"),
            ("Student Phone", s[6]),
            ("Guardian Phone", s[15]),
            ("Email", s[7]),
            ("Admission Date", s[13]),
            ("Present Address", s[8]),
            ("Permanent Address", s[9]),
        ]
        for k, v in details:
            row_f = tk.Frame(right, bg="white")
            row_f.pack(fill="x", pady=3)
            tk.Label(row_f, text=f"{k}:", font=("Segoe UI", 9, "bold"), bg="white", fg=COLORS["text_muted"], width=17, anchor="w").pack(side="left")
            tk.Label(row_f, text=v or "N/A", font=("Segoe UI", 9), bg="white", fg=COLORS["text_dark"], anchor="w").pack(side="left")

    # ==========================================================================
    # TEACHER MANAGEMENT
    # ==========================================================================
    def render_teachers(self):
        tk.Label(self.content_frame, text="Teacher Management", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        split = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        split.pack(fill="both", expand=True)

        form_card = tk.Frame(split, bg="white", padx=18, pady=18, width=340, highlightbackground=COLORS["border"], highlightthickness=1)
        form_card.pack(side="left", fill="y", padx=(0, 15))
        form_card.pack_propagate(False)

        tk.Label(form_card, text="Teacher Information", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 12))

        t_vars = {k: tk.StringVar() for k in ["teacher_id", "full_name", "subject", "phone", "email", "address"]}
        t_vars["teacher_id"].set(f"TCH-{datetime.now().year}-05")

        for label, key in [("Teacher ID *", "teacher_id"), ("Full Name *", "full_name"), ("Subject *", "subject"), ("Phone Number", "phone"), ("Email", "email"), ("Address", "address")]:
            tk.Label(form_card, text=label, font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(6, 2))
            ttk.Entry(form_card, textvariable=t_vars[key]).pack(fill="x")

        table_card = tk.Frame(split, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        table_card.pack(side="right", fill="both", expand=True)

        top_bar = tk.Frame(table_card, bg="white")
        top_bar.pack(fill="x", pady=(0, 10))
        tk.Label(top_bar, text="Faculty List", font=("Segoe UI", 12, "bold"), bg="white").pack(side="left")

        cols = ("Teacher ID", "Name", "Subject", "Phone", "Email", "Address")
        t_tree = ttk.Treeview(table_card, columns=cols, show="headings")
        for c in cols:
            t_tree.heading(c, text=c)
            t_tree.column(c, width=120, anchor="center")
        t_tree.pack(fill="both", expand=True)

        def load_teachers():
            for i in t_tree.get_children():
                t_tree.delete(i)
            conn = self.db.connect()
            for r in conn.execute("SELECT * FROM teachers"):
                t_tree.insert("", "end", values=r)
            conn.close()

        def save_teacher(is_update=False):
            tid = t_vars["teacher_id"].get().strip()
            name = t_vars["full_name"].get().strip()
            subj = t_vars["subject"].get().strip()
            if not tid or not name or not subj:
                messagebox.showerror("Validation Error", "Teacher ID, Name, and Subject are required!")
                return
            conn = self.db.connect()
            try:
                if is_update:
                    conn.execute(
                        "UPDATE teachers SET full_name=?, subject=?, phone=?, email=?, address=? WHERE teacher_id=?",
                        (name, subj, t_vars["phone"].get(), t_vars["email"].get(), t_vars["address"].get(), tid)
                    )
                else:
                    conn.execute(
                        "INSERT INTO teachers VALUES (?,?,?,?,?,?)",
                        (tid, name, subj, t_vars["phone"].get(), t_vars["email"].get(), t_vars["address"].get())
                    )
                conn.commit()
                messagebox.showinfo("Success", "Teacher record saved!")
                load_teachers()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Teacher ID already exists! Use Update instead.")
            finally:
                conn.close()

        btn_row = tk.Frame(form_card, bg="white")
        btn_row.pack(fill="x", pady=18)
        tk.Button(btn_row, text="➕ Add", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=7, command=lambda: save_teacher(False)).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(btn_row, text="✏️ Update", bg=COLORS["warning"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=7, command=lambda: save_teacher(True)).pack(side="left", fill="x", expand=True, padx=2)

        def on_select(e):
            sel = t_tree.selection()
            if sel:
                vals = t_tree.item(sel[0])["values"]
                for k, v in zip(["teacher_id", "full_name", "subject", "phone", "email", "address"], vals):
                    t_vars[k].set(v)

        t_tree.bind("<<TreeviewSelect>>", on_select)

        def delete_teacher():
            sel = t_tree.selection()
            if not sel:
                return
            tid = t_tree.item(sel[0])["values"][0]
            if messagebox.askyesno("Confirm", f"Delete Teacher {tid}?"):
                conn = self.db.connect()
                conn.execute("DELETE FROM teachers WHERE teacher_id=?", (tid,))
                conn.commit()
                conn.close()
                load_teachers()

        def view_teacher_profile():
            sel = t_tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a teacher first.")
                return
            v = t_tree.item(sel[0])["values"]
            messagebox.showinfo("Teacher Profile", f"ID: {v[0]}\nName: {v[1]}\nSubject: {v[2]}\nPhone: {v[3]}\nEmail: {v[4]}\nAddress: {v[5]}")

        tk.Button(top_bar, text="🗑️ Delete", bg=COLORS["danger"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, command=delete_teacher).pack(side="right", padx=4)
        tk.Button(top_bar, text="👁️ View Profile", bg=COLORS["info"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, command=view_teacher_profile).pack(side="right", padx=4)

        load_teachers()

    # ==========================================================================
    # CLASS & SECTION MANAGEMENT
    # ==========================================================================
    def render_classes(self):
        tk.Label(self.content_frame, text="Class & Section Management", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        split = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        split.pack(fill="both", expand=True)

        left_col = tk.Frame(split, bg=COLORS["bg_main"], width=360)
        left_col.pack(side="left", fill="y", padx=(0, 15))
        left_col.pack_propagate(False)

        cls_card = tk.Frame(left_col, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        cls_card.pack(fill="x", pady=(0, 12))
        tk.Label(cls_card, text="Create / Edit Class & Sections", font=("Segoe UI", 11, "bold"), bg="white", fg=COLORS["primary"]).pack(anchor="w")

        tk.Label(cls_card, text="Class Name (e.g., Class 11):", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(8, 2))
        cls_name_var = tk.StringVar()
        ttk.Entry(cls_card, textvariable=cls_name_var).pack(fill="x")

        tk.Label(cls_card, text="Sections (Comma separated, e.g., A,B,C):", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(8, 2))
        sec_list_var = tk.StringVar(value="A,B")
        ttk.Entry(cls_card, textvariable=sec_list_var).pack(fill="x")

        assign_card = tk.Frame(left_col, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        assign_card.pack(fill="both", expand=True)
        tk.Label(assign_card, text="Assign / Transfer Student", font=("Segoe UI", 11, "bold"), bg="white", fg=COLORS["success"]).pack(anchor="w", pady=(0, 8))

        tk.Label(assign_card, text="Student ID:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        assign_sid = tk.StringVar()
        ttk.Entry(assign_card, textvariable=assign_sid).pack(fill="x", pady=(2, 6))

        tk.Label(assign_card, text="Target Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        assign_cls = ttk.Combobox(assign_card, state="readonly")
        assign_cls.pack(fill="x", pady=(2, 6))

        tk.Label(assign_card, text="Target Section & New Roll:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        r_f = tk.Frame(assign_card, bg="white")
        r_f.pack(fill="x", pady=(2, 10))
        assign_sec = tk.StringVar(value="A")
        assign_roll = tk.StringVar(value="1")
        ttk.Entry(r_f, textvariable=assign_sec, width=12).pack(side="left", padx=(0, 5))
        ttk.Entry(r_f, textvariable=assign_roll, width=15).pack(side="left", fill="x", expand=True)

        right_col = tk.Frame(split, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        right_col.pack(side="right", fill="both", expand=True)

        top_f = tk.Frame(right_col, bg="white")
        top_f.pack(fill="x", pady=(0, 10))
        tk.Label(top_f, text="Select Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        view_cls_cb = ttk.Combobox(top_f, state="readonly", width=16)
        view_cls_cb.pack(side="left", padx=6)

        tk.Label(top_f, text="Section:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(10, 0))
        view_sec_cb = ttk.Combobox(top_f, values=["All"], state="readonly", width=12)
        view_sec_cb.set("All")
        view_sec_cb.pack(side="left", padx=6)

        cols = ("Student ID", "Full Name", "Class", "Section", "Roll", "Phone")
        c_tree = ttk.Treeview(right_col, columns=cols, show="headings")
        for c in cols:
            c_tree.heading(c, text=c)
            c_tree.column(c, width=110, anchor="center")
        c_tree.pack(fill="both", expand=True)

        def load_class_students(e=None):
            for i in c_tree.get_children():
                c_tree.delete(i)
            cn = view_cls_cb.get()
            sc = view_sec_cb.get()
            conn = self.db.connect()
            if sc == "All":
                rows = conn.execute("SELECT student_id, full_name, class_name, section, roll_number, phone FROM students WHERE class_name=? ORDER BY section, CAST(roll_number AS INTEGER)", (cn,)).fetchall()
            else:
                rows = conn.execute("SELECT student_id, full_name, class_name, section, roll_number, phone FROM students WHERE class_name=? AND section=? ORDER BY CAST(roll_number AS INTEGER)", (cn, sc)).fetchall()
            conn.close()
            for r in rows:
                c_tree.insert("", "end", values=r)

        def on_view_cls_change(e=None):
            cn = view_cls_cb.get()
            conn = self.db.connect()
            row = conn.execute("SELECT sections FROM classes WHERE class_name=?", (cn,)).fetchone()
            conn.close()
            if row:
                cls_name_var.set(cn)
                sec_list_var.set(row[0])
                secs = ["All"] + [s.strip() for s in row[0].split(",") if s.strip()]
                view_sec_cb.config(values=secs)
                view_sec_cb.set("All")
            load_class_students()

        def refresh_classes():
            conn = self.db.connect()
            cls_names = [r[0] for r in conn.execute("SELECT class_name FROM classes").fetchall()]
            conn.close()
            view_cls_cb.config(values=cls_names)
            assign_cls.config(values=cls_names)
            if cls_names:
                view_cls_cb.set(cls_names[0])
                assign_cls.set(cls_names[0])
                on_view_cls_change()

        def save_class(update=False):
            cn = cls_name_var.get().strip()
            sc = sec_list_var.get().strip()
            if not cn or not sc:
                messagebox.showerror("Error", "Class Name and Sections are required.")
                return
            conn = self.db.connect()
            try:
                if update:
                    conn.execute("UPDATE classes SET sections=? WHERE class_name=?", (sc, cn))
                else:
                    conn.execute("INSERT INTO classes (class_name, sections) VALUES (?, ?)", (cn, sc))
                conn.commit()
                refresh_classes()
                messagebox.showinfo("Success", "Class saved successfully!")
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate", "Class already exists! Use Update Sections.")
            finally:
                conn.close()

        b_row = tk.Frame(cls_card, bg="white")
        b_row.pack(fill="x", pady=10)
        tk.Button(b_row, text="➕ Create Class", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=6, command=lambda: save_class(False)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(b_row, text="✏️ Update Sections", bg=COLORS["warning"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=6, command=lambda: save_class(True)).pack(side="left", expand=True, fill="x", padx=2)

        def assign_student():
            conn = self.db.connect()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM students WHERE student_id=?", (assign_sid.get().strip(),))
            if not cur.fetchone():
                conn.close()
                messagebox.showerror("Not Found", "Student ID not found!")
                return
            try:
                cur.execute(
                    "UPDATE students SET class_name=?, section=?, roll_number=? WHERE student_id=?",
                    (assign_cls.get(), assign_sec.get().strip(), assign_roll.get().strip(), assign_sid.get().strip())
                )
                conn.commit()
                messagebox.showinfo("Assigned", "Student class/section updated!")
                load_class_students()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Roll number already taken in target class/section.")
            finally:
                conn.close()

        tk.Button(assign_card, text="🔄 Assign Student to Class", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=7, command=assign_student).pack(fill="x")

        def delete_selected_class():
            cn = view_cls_cb.get()
            if cn and messagebox.askyesno("Confirm", f"Delete {cn}?"):
                conn = self.db.connect()
                conn.execute("DELETE FROM classes WHERE class_name=?", (cn,))
                conn.commit()
                conn.close()
                refresh_classes()

        tk.Button(top_f, text="🗑️ Delete Class", bg=COLORS["danger"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, command=delete_selected_class).pack(side="right")

        view_cls_cb.bind("<<ComboboxSelected>>", on_view_cls_change)
        view_sec_cb.bind("<<ComboboxSelected>>", load_class_students)
        refresh_classes()

    # ==========================================================================
    # ATTENDANCE MANAGEMENT (WITH LATE MINUTES ENTRY & REPORT)
    # ==========================================================================
    def render_attendance(self):
        tk.Label(self.content_frame, text="Attendance Management", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True)

        tab_take = tk.Frame(notebook, bg="white", padx=15, pady=15)
        tab_report = tk.Frame(notebook, bg="white", padx=15, pady=15)
        notebook.add(tab_take, text="  📋 Take Daily Attendance  ")
        notebook.add(tab_report, text="  📊 Date & Monthly Attendance Report  ")

        ctrl_f = tk.Frame(tab_take, bg="white")
        ctrl_f.pack(fill="x", pady=(0, 10))

        conn = self.db.connect()
        class_rows = conn.execute("SELECT class_name, sections FROM classes").fetchall()
        conn.close()
        class_sec_map = {r[0]: [s.strip() for s in r[1].split(",") if s.strip()] for r in class_rows}
        classes = list(class_sec_map.keys())

        tk.Label(ctrl_f, text="Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        att_cls = ttk.Combobox(ctrl_f, values=classes, state="readonly", width=15)
        att_cls.pack(side="left", padx=6)

        tk.Label(ctrl_f, text="Section:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        att_sec_cb = ttk.Combobox(ctrl_f, state="readonly", width=14)
        att_sec_cb.pack(side="left", padx=6)

        tk.Label(ctrl_f, text="Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        att_date = tk.StringVar(value=date.today().isoformat())
        ent_att_date = ttk.Entry(ctrl_f, textvariable=att_date, width=14)
        ent_att_date.pack(side="left", padx=6)

        att_rows_frame = tk.Frame(tab_take, bg="white")
        att_rows_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(att_rows_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(att_rows_frame, orient="vertical", command=canvas.yview)
        scroll_inner = tk.Frame(canvas, bg="white")
        scroll_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Stores (status_var, late_mins_var, section_val) per student_id
        status_vars = {}

        def load_att_students(event=None):
            for w in scroll_inner.winfo_children():
                w.destroy()
            status_vars.clear()

            selected_cls = att_cls.get().strip()
            selected_sec = att_sec_cb.get().strip()
            selected_dt = att_date.get().strip()

            conn = self.db.connect()
            if selected_sec == "All":
                students = conn.execute(
                    "SELECT student_id, roll_number, full_name, section FROM students WHERE class_name=? AND status='Active' ORDER BY section, CAST(roll_number AS INTEGER)",
                    (selected_cls,)
                ).fetchall()
            else:
                students = conn.execute(
                    "SELECT student_id, roll_number, full_name, section FROM students WHERE class_name=? AND section=? AND status='Active' ORDER BY CAST(roll_number AS INTEGER)",
                    (selected_cls, selected_sec)
                ).fetchall()

            existing_rows = conn.execute(
                "SELECT student_id, status, COALESCE(late_minutes, 0) FROM attendance WHERE class_name=? AND att_date=?",
                (selected_cls, selected_dt)
            ).fetchall()
            conn.close()
            existing = {r[0]: (r[1], r[2]) for r in existing_rows}

            if not students:
                tk.Label(
                    scroll_inner,
                    text=f"No active students found in {selected_cls} (Section: {selected_sec}).",
                    font=("Segoe UI", 11), bg="white", fg=COLORS["text_muted"]
                ).pack(pady=30)
                return

            hdr = tk.Frame(scroll_inner, bg="#E2E8F0", pady=7)
            hdr.pack(fill="x")
            tk.Label(hdr, text="Roll", width=6, font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left")
            tk.Label(hdr, text="Student ID", width=14, font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left")
            tk.Label(hdr, text="Full Name", width=22, anchor="w", font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left")
            tk.Label(hdr, text="Section", width=10, font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left")
            tk.Label(hdr, text="Status", width=34, font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left")
            tk.Label(hdr, text="Late Minutes", width=14, font=("Segoe UI", 9, "bold"), bg="#E2E8F0").pack(side="left", padx=6)

            for sid, roll, name, sec_val in students:
                row_f = tk.Frame(scroll_inner, bg="white", pady=6, highlightbackground="#F1F5F9", highlightthickness=1)
                row_f.pack(fill="x")
                tk.Label(row_f, text=roll, width=6, bg="white").pack(side="left")
                tk.Label(row_f, text=sid, width=14, bg="white").pack(side="left")
                tk.Label(row_f, text=name, width=22, anchor="w", bg="white", font=("Segoe UI", 9, "bold")).pack(side="left")
                tk.Label(row_f, text=sec_val, width=10, bg="white", fg=COLORS["primary"]).pack(side="left")

                prev_st, prev_mins = existing.get(sid, ("Present", 0))
                var = tk.StringVar(value=prev_st)
                mins_var = tk.StringVar(value=str(prev_mins if prev_st == "Late" else 0))

                late_box_f = tk.Frame(row_f, bg="white")
                ent_mins = ttk.Entry(late_box_f, textvariable=mins_var, width=7, justify="center")
                lbl_min = tk.Label(late_box_f, text="mins", font=("Segoe UI", 8), bg="white", fg=COLORS["text_muted"])

                def toggle_late_input(s_var=var, m_var=mins_var, box=late_box_f, entry=ent_mins, unit=lbl_min):
                    if s_var.get() == "Late":
                        entry.config(state="normal")
                        if not m_var.get().strip() or m_var.get().strip() == "0":
                            m_var.set("5")
                        box.pack(side="left", padx=8)
                        entry.pack(side="left")
                        unit.pack(side="left", padx=(3, 0))
                    else:
                        m_var.set("0")
                        entry.config(state="disabled")
                        box.pack_forget()

                for st in ["Present", "Absent", "Late", "Leave"]:
                    tk.Radiobutton(
                        row_f, text=st, variable=var, value=st, bg="white",
                        command=toggle_late_input
                    ).pack(side="left", padx=5)

                toggle_late_input()
                status_vars[sid] = (var, mins_var, sec_val)

        def on_att_class_change(event=None):
            selected_cls = att_cls.get().strip()
            secs = class_sec_map.get(selected_cls, [])
            conn = self.db.connect()
            db_secs = [r[0] for r in conn.execute("SELECT DISTINCT section FROM students WHERE class_name=? AND section IS NOT NULL AND section != ''", (selected_cls,)).fetchall()]
            conn.close()
            merged = ["All"] + list(dict.fromkeys(secs + db_secs))
            att_sec_cb.config(values=merged)
            chosen = "All"
            for s in merged[1:]:
                conn = self.db.connect()
                cnt = conn.execute("SELECT COUNT(*) FROM students WHERE class_name=? AND section=? AND status='Active'", (selected_cls, s)).fetchone()[0]
                conn.close()
                if cnt > 0:
                    chosen = s
                    break
            att_sec_cb.set(chosen)
            load_att_students()

        def save_attendance():
            if not status_vars:
                messagebox.showwarning("No Students", "No students loaded to save attendance.")
                return
            selected_cls = att_cls.get().strip()
            selected_dt = att_date.get().strip()
            if not selected_dt:
                messagebox.showerror("Validation Error", "Please enter a valid date (YYYY-MM-DD).")
                return

            prepared = []
            for sid, (var, mins_var, sec_val) in status_vars.items():
                st_val = var.get()
                if st_val == "Late":
                    raw_m = mins_var.get().strip()
                    try:
                        l_mins = int(float(raw_m))
                        if l_mins < 0:
                            messagebox.showerror("Validation Error", f"Late minutes for {sid} cannot be negative.")
                            return
                    except ValueError:
                        messagebox.showerror("Validation Error", f"Please enter valid late minutes (number) for {sid}.")
                        return
                else:
                    l_mins = 0
                prepared.append((sid, selected_cls, sec_val, selected_dt, st_val, l_mins))

            conn = self.db.connect()
            for rec in prepared:
                conn.execute("""
                    INSERT INTO attendance (student_id, class_name, section, att_date, status, late_minutes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, att_date) DO UPDATE SET
                        status=excluded.status,
                        late_minutes=excluded.late_minutes,
                        section=excluded.section
                """, rec)
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", f"Attendance (including late minutes) saved for {len(prepared)} students on {selected_dt}!")
            generate_att_report()

        att_cls.bind("<<ComboboxSelected>>", on_att_class_change)
        att_sec_cb.bind("<<ComboboxSelected>>", load_att_students)
        ent_att_date.bind("<Return>", load_att_students)

        tk.Button(ctrl_f, text="🔍 Load Students", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2", command=load_att_students).pack(side="left", padx=8)
        tk.Button(ctrl_f, text="💾 Save Attendance", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=14, pady=5, cursor="hand2", command=save_attendance).pack(side="right")

        # --- TAB 2: DATE-WISE & MONTHLY ATTENDANCE REPORT ---
        rep_ctrl = tk.Frame(tab_report, bg="white")
        rep_ctrl.pack(fill="x", pady=(0, 10))

        tk.Label(rep_ctrl, text="Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        rep_cls = ttk.Combobox(rep_ctrl, values=classes, state="readonly", width=14)
        if classes:
            rep_cls.set(classes[0])
        rep_cls.pack(side="left", padx=5)

        tk.Label(rep_ctrl, text="Month (YYYY-MM) or Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(10, 4))
        rep_period = tk.StringVar(value=date.today().strftime("%Y-%m"))
        ttk.Entry(rep_ctrl, textvariable=rep_period, width=15).pack(side="left", padx=5)

        cols = ("Student ID", "Name", "Section", "Total Days", "Present", "Absent", "Late", "Late Mins", "Leave", "Percentage (%)")
        rep_tree = ttk.Treeview(tab_report, columns=cols, show="headings")
        for c in cols:
            rep_tree.heading(c, text=c)
            rep_tree.column(c, width=98, anchor="center")
        rep_tree.pack(fill="both", expand=True)

        def generate_att_report(event=None):
            for i in rep_tree.get_children():
                rep_tree.delete(i)
            period = f"{rep_period.get().strip()}%"
            conn = self.db.connect()
            students = conn.execute("SELECT student_id, full_name, section FROM students WHERE class_name=?", (rep_cls.get(),)).fetchall()
            for sid, name, sec in students:
                recs = conn.execute("SELECT status, COALESCE(late_minutes, 0) FROM attendance WHERE student_id=? AND att_date LIKE ?", (sid, period)).fetchall()
                statuses = [r[0] for r in recs]
                tot_late_mins = sum(int(r[1] or 0) for r in recs if r[0] == "Late")
                tot = len(statuses)
                p = statuses.count("Present")
                a = statuses.count("Absent")
                l = statuses.count("Late")
                lv = statuses.count("Leave")
                pct = round(((p + l) / tot) * 100, 2) if tot > 0 else 0.0
                rep_tree.insert("", "end", values=(sid, name, sec, tot, p, a, l, f"{tot_late_mins} min", lv, f"{pct}%"))
            conn.close()

        rep_cls.bind("<<ComboboxSelected>>", generate_att_report)
        tk.Button(rep_ctrl, text="📊 Generate Report", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2", command=generate_att_report).pack(side="left", padx=8)

        if classes:
            att_cls.set(classes[0])
            on_att_class_change()
        generate_att_report()

    # ==========================================================================
    # EXAMINATION & RESULT MANAGEMENT
    # ==========================================================================
    def render_exams(self):
        tk.Label(self.content_frame, text="Examination & Result Management", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True)

        tab_setup = tk.Frame(notebook, bg="white", padx=15, pady=15)
        tab_marks = tk.Frame(notebook, bg="white", padx=15, pady=15)
        tab_result = tk.Frame(notebook, bg="white", padx=15, pady=15)
        notebook.add(tab_setup, text="  ⚙️ Exams & Subjects  ")
        notebook.add(tab_marks, text="  ✍️ Enter Student Marks  ")
        notebook.add(tab_result, text="  🎓 Results & Marksheet  ")

        s_grid = tk.Frame(tab_setup, bg="white")
        s_grid.pack(fill="both", expand=True)

        ex_f = tk.Frame(s_grid, bg="#F8FAFC", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        ex_f.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(ex_f, text="Add New Examination", font=("Segoe UI", 12, "bold"), bg="#F8FAFC", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 10))
        ex_name_var = tk.StringVar()
        ex_date_var = tk.StringVar(value=date.today().isoformat())
        tk.Label(ex_f, text="Exam Name:", bg="#F8FAFC", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(ex_f, textvariable=ex_name_var).pack(fill="x", pady=(2, 8))
        tk.Label(ex_f, text="Exam Date:", bg="#F8FAFC", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(ex_f, textvariable=ex_date_var).pack(fill="x", pady=(2, 10))

        ex_list = ttk.Treeview(ex_f, columns=("Exam", "Date"), show="headings", height=8)
        ex_list.heading("Exam", text="Exam Name")
        ex_list.heading("Date", text="Date")
        ex_list.pack(fill="both", expand=True, pady=(10, 0))

        sub_f = tk.Frame(s_grid, bg="#F8FAFC", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        sub_f.pack(side="right", fill="both", expand=True, padx=(10, 0))
        tk.Label(sub_f, text="Add New Subject", font=("Segoe UI", 12, "bold"), bg="#F8FAFC", fg=COLORS["success"]).pack(anchor="w", pady=(0, 10))
        sub_name_var = tk.StringVar()
        sub_full_var = tk.StringVar(value="100")
        tk.Label(sub_f, text="Subject Name:", bg="#F8FAFC", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(sub_f, textvariable=sub_name_var).pack(fill="x", pady=(2, 8))
        tk.Label(sub_f, text="Full Marks:", bg="#F8FAFC", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(sub_f, textvariable=sub_full_var).pack(fill="x", pady=(2, 10))

        sub_list = ttk.Treeview(sub_f, columns=("Subject", "Full Marks"), show="headings", height=8)
        sub_list.heading("Subject", text="Subject Name")
        sub_list.heading("Full Marks", text="Full Marks")
        sub_list.pack(fill="both", expand=True, pady=(10, 0))

        m_top = tk.Frame(tab_marks, bg="white")
        m_top.pack(fill="x", pady=(0, 12))

        tk.Label(m_top, text="Exam:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        m_exam_cb = ttk.Combobox(m_top, state="readonly", width=22)
        m_exam_cb.pack(side="left", padx=5)

        tk.Label(m_top, text="Subject:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(8, 0))
        m_sub_cb = ttk.Combobox(m_top, state="readonly", width=18)
        m_sub_cb.pack(side="left", padx=5)

        conn = self.db.connect()
        classes = [r[0] for r in conn.execute("SELECT class_name FROM classes").fetchall()]
        conn.close()

        tk.Label(m_top, text="Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(8, 0))
        m_cls_cb = ttk.Combobox(m_top, values=classes, state="readonly", width=14)
        if classes:
            m_cls_cb.set(classes[0])
        m_cls_cb.pack(side="left", padx=5)

        r_top = tk.Frame(tab_result, bg="white")
        r_top.pack(fill="x", pady=(0, 10))

        tk.Label(r_top, text="Exam:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
        r_exam_cb = ttk.Combobox(r_top, state="readonly", width=22)
        r_exam_cb.pack(side="left", padx=5)

        tk.Label(r_top, text="Class:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left", padx=(8, 0))
        r_cls_cb = ttk.Combobox(r_top, values=classes, state="readonly", width=14)
        if classes:
            r_cls_cb.set(classes[0])
        r_cls_cb.pack(side="left", padx=5)

        def refresh_exam_subj():
            for i in ex_list.get_children():
                ex_list.delete(i)
            for i in sub_list.get_children():
                sub_list.delete(i)
            conn = self.db.connect()
            exams = conn.execute("SELECT exam_name, exam_date FROM exams").fetchall()
            subs = conn.execute("SELECT subject_name, full_marks FROM subjects").fetchall()
            conn.close()
            for r in exams:
                ex_list.insert("", "end", values=r)
            for r in subs:
                sub_list.insert("", "end", values=r)
            m_exam_cb.config(values=[r[0] for r in exams])
            r_exam_cb.config(values=[r[0] for r in exams])
            m_sub_cb.config(values=[r[0] for r in subs])
            if exams:
                m_exam_cb.set(exams[0][0])
                r_exam_cb.set(exams[0][0])
            if subs:
                m_sub_cb.set(subs[0][0])

        def add_exam():
            if not ex_name_var.get().strip():
                return
            conn = self.db.connect()
            try:
                conn.execute("INSERT INTO exams (exam_name, exam_date) VALUES (?, ?)", (ex_name_var.get().strip(), ex_date_var.get().strip()))
                conn.commit()
                ex_name_var.set("")
                refresh_exam_subj()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Exam already exists.")
            finally:
                conn.close()

        def add_subject():
            if not sub_name_var.get().strip():
                return
            conn = self.db.connect()
            try:
                conn.execute("INSERT INTO subjects (subject_name, full_marks) VALUES (?, ?)", (sub_name_var.get().strip(), float(sub_full_var.get())))
                conn.commit()
                sub_name_var.set("")
                refresh_exam_subj()
            except Exception as e:
                messagebox.showerror("Error", f"Could not add subject: {e}")
            finally:
                conn.close()

        tk.Button(ex_f, text="➕ Add Exam", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=6, command=add_exam).pack(fill="x")
        tk.Button(sub_f, text="➕ Add Subject", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=6, command=add_subject).pack(fill="x")

        marks_container = tk.Frame(tab_marks, bg="white")
        marks_container.pack(fill="both", expand=True)
        mark_entries = {}

        def load_students_for_marks():
            for w in marks_container.winfo_children():
                w.destroy()
            mark_entries.clear()
            conn = self.db.connect()
            students = conn.execute("SELECT student_id, roll_number, full_name FROM students WHERE class_name=? ORDER BY CAST(roll_number AS INTEGER)", (m_cls_cb.get(),)).fetchall()
            existing = dict(conn.execute("SELECT student_id, marks_obtained FROM marks WHERE exam_name=? AND subject_name=?", (m_exam_cb.get(), m_sub_cb.get())).fetchall())
            conn.close()

            for sid, roll, name in students:
                rf = tk.Frame(marks_container, bg="white", pady=4)
                rf.pack(fill="x")
                tk.Label(rf, text=f"Roll {roll}  |  {sid}  -  {name}", width=45, anchor="w", bg="white", font=("Segoe UI", 10)).pack(side="left")
                mv = tk.StringVar(value=str(existing.get(sid, "")))
                mark_entries[sid] = mv
                ttk.Entry(rf, textvariable=mv, width=15).pack(side="left", padx=10)

        def save_all_marks():
            conn = self.db.connect()
            sub_row = conn.execute("SELECT full_marks FROM subjects WHERE subject_name=?", (m_sub_cb.get(),)).fetchone()
            full_m = sub_row[0] if sub_row else 100.0
            saved = 0
            for sid, mv in mark_entries.items():
                val = mv.get().strip()
                if val != "":
                    try:
                        num = float(val)
                        conn.execute("""
                            INSERT INTO marks (exam_name, student_id, subject_name, marks_obtained, full_marks)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(exam_name, student_id, subject_name) DO UPDATE SET marks_obtained=excluded.marks_obtained
                        """, (m_exam_cb.get(), sid, m_sub_cb.get(), num, full_m))
                        saved += 1
                    except ValueError:
                        pass
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", f"Marks saved for {saved} students!")

        tk.Button(m_top, text="Load List", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, command=load_students_for_marks).pack(side="left", padx=6)
        tk.Button(m_top, text="💾 Save Marks", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, command=save_all_marks).pack(side="right")

        res_cols = ("Student ID", "Name", "Roll", "Subjects", "Total Marks", "Percentage", "Grade", "GPA")
        res_tree = ttk.Treeview(tab_result, columns=res_cols, show="headings")
        for c in res_cols:
            res_tree.heading(c, text=c)
            res_tree.column(c, width=110, anchor="center")
        res_tree.pack(fill="both", expand=True)

        def load_class_results():
            for i in res_tree.get_children():
                res_tree.delete(i)
            conn = self.db.connect()
            students = conn.execute("SELECT student_id, full_name, roll_number FROM students WHERE class_name=? ORDER BY CAST(roll_number AS INTEGER)", (r_cls_cb.get(),)).fetchall()
            for sid, name, roll in students:
                m_rows = conn.execute("SELECT marks_obtained, full_marks FROM marks WHERE exam_name=? AND student_id=?", (r_exam_cb.get(), sid)).fetchall()
                if not m_rows:
                    continue
                obt = sum(r[0] for r in m_rows)
                tot = sum(r[1] for r in m_rows)
                pct = round((obt / tot) * 100, 2) if tot > 0 else 0
                grade, gpa = calculate_grade_gpa(pct)
                if any((r[0] / r[1]) * 100 < 33 for r in m_rows):
                    grade, gpa = "F", 0.00
                res_tree.insert("", "end", values=(sid, name, roll, len(m_rows), f"{obt}/{tot}", f"{pct}%", grade, f"{gpa:.2f}"))
            conn.close()

        def generate_and_print_marksheet():
            sel = res_tree.selection()
            if not sel:
                messagebox.showwarning("Select Student", "Please select a student row to generate/print Marksheet.")
                return
            vals = res_tree.item(sel[0])["values"]
            sid, sname, roll = vals[0], vals[1], vals[2]
            exam = r_exam_cb.get()

            conn = self.db.connect()
            school = conn.execute("SELECT school_name, address FROM settings WHERE id=1").fetchone()
            stu = conn.execute("SELECT father_name, mother_name, class_name, section FROM students WHERE student_id=?", (sid,)).fetchone()
            sub_marks = conn.execute("SELECT subject_name, full_marks, marks_obtained FROM marks WHERE exam_name=? AND student_id=?", (exam, sid)).fetchall()
            conn.close()

            rows = []
            for sub, fm, om in sub_marks:
                pct = (om / fm) * 100
                g, gp = calculate_grade_gpa(pct)
                rows.append([sub, fm, om, g, f"{gp:.2f}"])
            rows.append(["TOTAL / FINAL", "", vals[4], vals[6], f"GPA: {vals[7]}"])

            subtitle = f"{school[1]} | Exam: {exam} | Student: {sname} (ID: {sid}, Class: {stu[2]}-{stu[3]}, Roll: {roll})"
            path = export_printable_document(f"Marksheet_{sid}_{exam.replace(' ', '_')}.html", f"{school[0]} - ACADEMIC MARKSHEET", subtitle, ["Subject", "Full Marks", "Obtained", "Grade", "GPA"], rows)
            open_file_for_print(path)

        tk.Button(r_top, text="🔍 View Class Result", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, command=load_class_results).pack(side="left", padx=6)
        tk.Button(r_top, text="🖨️ Generate & Print Marksheet", bg=COLORS["purple"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, command=generate_and_print_marksheet).pack(side="right")

        refresh_exam_subj()

    # ==========================================================================
    # FEES MANAGEMENT
    # ==========================================================================
    def render_fees(self):
        tk.Label(self.content_frame, text="Fees Collection & Payment Management", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        split = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        split.pack(fill="both", expand=True)

        form_card = tk.Frame(split, bg="white", padx=18, pady=18, width=350, highlightbackground=COLORS["border"], highlightthickness=1)
        form_card.pack(side="left", fill="y", padx=(0, 15))
        form_card.pack_propagate(False)

        tk.Label(form_card, text="Collect Student Fee", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 10))

        f_sid = tk.StringVar()
        f_type = tk.StringVar(value="Monthly Fees")
        f_total = tk.StringVar(value="1500")
        f_paid = tk.StringVar(value="1500")
        f_due = tk.StringVar(value="0.00")
        f_status = tk.StringVar(value="Paid")

        def calc_due(*args):
            try:
                tot = float(f_total.get() or 0)
                paid = float(f_paid.get() or 0)
                due = max(0.0, tot - paid)
                f_due.set(f"{due:.2f}")
                f_status.set("Paid" if due == 0 else "Unpaid / Partial")
            except ValueError:
                pass

        f_total.trace_add("write", calc_due)
        f_paid.trace_add("write", calc_due)

        tk.Label(form_card, text="Student ID *:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Entry(form_card, textvariable=f_sid).pack(fill="x", pady=(2, 8))

        tk.Label(form_card, text="Fee Category:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Combobox(form_card, textvariable=f_type, values=["Monthly Fees", "Admission Fees", "Exam Fees", "Lab / Library Fees", "Transport Fees"], state="readonly").pack(fill="x", pady=(2, 8))

        tk.Label(form_card, text="Total Fee Amount:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Entry(form_card, textvariable=f_total).pack(fill="x", pady=(2, 8))

        tk.Label(form_card, text="Paid Amount:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Entry(form_card, textvariable=f_paid).pack(fill="x", pady=(2, 8))

        tk.Label(form_card, text="Due Amount (Auto):", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Entry(form_card, textvariable=f_due, state="readonly").pack(fill="x", pady=(2, 8))

        tk.Label(form_card, text="Payment Status:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
        ttk.Combobox(form_card, textvariable=f_status, values=["Paid", "Unpaid / Partial"], state="readonly").pack(fill="x", pady=(2, 14))

        right_card = tk.Frame(split, bg="white", padx=15, pady=15, highlightbackground=COLORS["border"], highlightthickness=1)
        right_card.pack(side="right", fill="both", expand=True)

        top_f = tk.Frame(right_card, bg="white")
        top_f.pack(fill="x", pady=(0, 10))
        tk.Label(top_f, text="Payment History & Receipts", font=("Segoe UI", 12, "bold"), bg="white").pack(side="left")

        cols = ("Receipt No", "Student ID", "Student Name", "Fee Type", "Total", "Paid", "Due", "Status", "Date")
        fee_tree = ttk.Treeview(right_card, columns=cols, show="headings")
        for c in cols:
            fee_tree.heading(c, text=c)
            fee_tree.column(c, width=95, anchor="center")
        fee_tree.pack(fill="both", expand=True)

        def load_fees():
            for i in fee_tree.get_children():
                fee_tree.delete(i)
            conn = self.db.connect()
            q = """
                SELECT f.receipt_no, f.student_id, s.full_name, f.fee_type, f.total_amount, f.paid_amount, f.due_amount, f.status, f.payment_date
                FROM fees f JOIN students s ON f.student_id = s.student_id ORDER BY f.id DESC
            """
            for r in conn.execute(q):
                fee_tree.insert("", "end", values=r)
            conn.close()

        def record_fee():
            sid = f_sid.get().strip()
            if not sid:
                messagebox.showerror("Error", "Please enter Student ID.")
                return
            conn = self.db.connect()
            stu = conn.execute("SELECT full_name FROM students WHERE student_id=?", (sid,)).fetchone()
            if not stu:
                conn.close()
                messagebox.showerror("Error", "Invalid Student ID!")
                return
            rcp = f"RCP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn.execute("""
                INSERT INTO fees (receipt_no, student_id, fee_type, total_amount, paid_amount, due_amount, status, payment_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (rcp, sid, f_type.get(), float(f_total.get()), float(f_paid.get()), float(f_due.get()), f_status.get(), date.today().isoformat()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Fee recorded! Receipt No: {rcp}")
            load_fees()

        tk.Button(form_card, text="💳 Record Payment", bg=COLORS["success"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, pady=8, cursor="hand2", command=record_fee).pack(fill="x")

        def print_money_receipt():
            sel = fee_tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a payment record to print Money Receipt.")
                return
            v = fee_tree.item(sel[0])["values"]
            conn = self.db.connect()
            school = conn.execute("SELECT school_name, address, phone FROM settings WHERE id=1").fetchone()
            conn.close()
            rows = [
                ["Receipt Number", v[0]],
                ["Payment Date", v[8]],
                ["Student ID & Name", f"{v[1]} - {v[2]}"],
                ["Fee Category", v[3]],
                ["Total Fee", f"{v[4]}"],
                ["Paid Amount", f"{v[5]}"],
                ["Due Balance", f"{v[6]}"],
                ["Payment Status", v[7]],
            ]
            path = export_printable_document(f"Receipt_{v[0]}.html", f"{school[0]} - MONEY RECEIPT", f"{school[1]} | Tel: {school[2]}", ["Field", "Details"], rows)
            open_file_for_print(path)

        tk.Button(top_f, text="🧾 Generate & Print Receipt", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, command=print_money_receipt).pack(side="right")

        load_fees()

    # ==========================================================================
    # REPORTS (EXCEL/CSV & PRINTABLE HTML)
    # ==========================================================================
    def render_reports(self):
        tk.Label(self.content_frame, text="Reports Center (Excel/CSV & Print)", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        ctrl_card = tk.Frame(self.content_frame, bg="white", padx=15, pady=12, highlightbackground=COLORS["border"], highlightthickness=1)
        ctrl_card.pack(fill="x", pady=(0, 12))

        tk.Label(ctrl_card, text="Select Report Type:", font=("Segoe UI", 10, "bold"), bg="white").pack(side="left")
        rep_type = ttk.Combobox(ctrl_card, values=[
            "Student List Report",
            "Class-wise Student Report",
            "Attendance Report",
            "Examination Result Report",
            "Fees Collection Report",
            "Due Fees Report"
        ], state="readonly", width=28)
        rep_type.set("Student List Report")
        rep_type.pack(side="left", padx=10)

        table_card = tk.Frame(self.content_frame, bg="white", padx=12, pady=12, highlightbackground=COLORS["border"], highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        rep_tree = ttk.Treeview(table_card, show="headings")
        rep_tree.pack(fill="both", expand=True)

        current_data = {"headers": [], "rows": [], "title": ""}

        def load_selected_report(e=None):
            rtype = rep_type.get()
            current_data["title"] = rtype
            conn = self.db.connect()
            if rtype == "Student List Report":
                headers = ["Student ID", "Full Name", "Gender", "Class", "Section", "Roll", "Phone", "Status"]
                rows = conn.execute("SELECT student_id, full_name, gender, class_name, section, roll_number, phone, status FROM students").fetchall()
            elif rtype == "Class-wise Student Report":
                headers = ["Class", "Section", "Total Students", "Male", "Female"]
                rows = conn.execute("""
                    SELECT class_name, section, COUNT(*),
                    SUM(CASE WHEN gender='Male' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN gender='Female' THEN 1 ELSE 0 END)
                    FROM students GROUP BY class_name, section
                """).fetchall()
            elif rtype == "Attendance Report":
                headers = ["Date", "Class", "Section", "Student ID", "Status", "Late Mins"]
                rows = conn.execute("SELECT att_date, class_name, section, student_id, status, COALESCE(late_minutes, 0) FROM attendance ORDER BY att_date DESC").fetchall()
            elif rtype == "Examination Result Report":
                headers = ["Exam", "Student ID", "Subject", "Marks Obtained", "Full Marks"]
                rows = conn.execute("SELECT exam_name, student_id, subject_name, marks_obtained, full_marks FROM marks").fetchall()
            elif rtype == "Fees Collection Report":
                headers = ["Receipt No", "Student ID", "Fee Type", "Total", "Paid", "Due", "Status", "Date"]
                rows = conn.execute("SELECT receipt_no, student_id, fee_type, total_amount, paid_amount, due_amount, status, payment_date FROM fees").fetchall()
            else:
                headers = ["Receipt No", "Student ID", "Fee Type", "Total", "Paid", "Due Amount", "Date"]
                rows = conn.execute("SELECT receipt_no, student_id, fee_type, total_amount, paid_amount, due_amount, payment_date FROM fees WHERE due_amount > 0").fetchall()
            conn.close()

            current_data["headers"] = headers
            current_data["rows"] = rows

            rep_tree.delete(*rep_tree.get_children())
            rep_tree["columns"] = headers
            for h in headers:
                rep_tree.heading(h, text=h)
                rep_tree.column(h, width=120, anchor="center")
            for r in rows:
                rep_tree.insert("", "end", values=r)

        def do_export_excel():
            fn = f"{current_data['title'].replace(' ', '_')}_{date.today()}.csv"
            path = export_to_csv(fn, current_data["headers"], current_data["rows"])
            messagebox.showinfo("Excel/CSV Exported", f"Report exported successfully to:\n{path}")

        def do_export_printable(auto_print=False):
            fn = f"{current_data['title'].replace(' ', '_')}_{date.today()}.html"
            path = export_printable_document(fn, current_data["title"], f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", current_data["headers"], current_data["rows"])
            if auto_print:
                open_file_for_print(path)
            else:
                messagebox.showinfo("Document Saved", f"Printable report saved at:\n{path}")

        rep_type.bind("<<ComboboxSelected>>", load_selected_report)
        tk.Button(ctrl_card, text="📊 Export Excel (CSV)", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=6, command=do_export_excel).pack(side="right", padx=4)
        tk.Button(ctrl_card, text="📄 Export Document", bg=COLORS["danger"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=6, command=lambda: do_export_printable(False)).pack(side="right", padx=4)
        tk.Button(ctrl_card, text="🖨️ Print Report", bg=COLORS["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=6, command=lambda: do_export_printable(True)).pack(side="right", padx=4)

        load_selected_report()

    # ==========================================================================
    # SETTINGS, ADMIN PROFILE, CHANGE PASSWORD, BACKUP & RESTORE
    # ==========================================================================
    def render_settings(self):
        tk.Label(self.content_frame, text="System Settings, Admin Profile & Database Backup", font=("Segoe UI", 17, "bold"), bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", pady=(0, 12))

        grid = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        sch_card = tk.Frame(grid, bg="white", padx=18, pady=18, highlightbackground=COLORS["border"], highlightthickness=1)
        sch_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        tk.Label(sch_card, text="🏛️ School / College Configuration", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 10))

        conn = self.db.connect()
        s_row = conn.execute("SELECT school_name, address, phone, email, logo_path FROM settings WHERE id=1").fetchone()
        conn.close()

        sch_name = tk.StringVar(value=s_row[0])
        sch_addr = tk.StringVar(value=s_row[1])
        sch_phone = tk.StringVar(value=s_row[2])
        sch_email = tk.StringVar(value=s_row[3])
        logo_state = {"path": s_row[4]}

        for lbl, var in [("Institution Name:", sch_name), ("Address:", sch_addr), ("Phone:", sch_phone), ("Email:", sch_email)]:
            tk.Label(sch_card, text=lbl, font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(4, 2))
            ttk.Entry(sch_card, textvariable=var).pack(fill="x")

        def upload_logo():
            f = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.gif")])
            if f:
                dest = os.path.join(ASSETS_DIR, f"school_logo{os.path.splitext(f)[1]}")
                shutil.copy(f, dest)
                logo_state["path"] = dest
                messagebox.showinfo("Logo Selected", "Logo uploaded! Click Save Settings to apply.")

        def save_school_settings():
            conn = self.db.connect()
            conn.execute(
                "UPDATE settings SET school_name=?, address=?, phone=?, email=?, logo_path=? WHERE id=1",
                (sch_name.get().strip(), sch_addr.get().strip(), sch_phone.get().strip(), sch_email.get().strip(), logo_state["path"])
            )
            conn.commit()
            conn.close()
            self.refresh_school_header()
            messagebox.showinfo("Saved", "School/College information updated!")

        b_f = tk.Frame(sch_card, bg="white")
        b_f.pack(fill="x", pady=14)
        tk.Button(b_f, text="🖼️ Set School Logo", bg=COLORS["info"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=7, command=upload_logo).pack(side="left", padx=(0, 8))
        tk.Button(b_f, text="💾 Save Settings", bg=COLORS["success"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=14, pady=7, command=save_school_settings).pack(side="left")

        adm_card = tk.Frame(grid, bg="white", padx=18, pady=18, highlightbackground=COLORS["border"], highlightthickness=1)
        adm_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        tk.Label(adm_card, text="🔐 Admin Profile & Change Password", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["purple"]).pack(anchor="w", pady=(0, 10))

        adm_fullname = tk.StringVar(value=self.admin_user["full_name"])
        old_pass = tk.StringVar()
        new_pass = tk.StringVar()
        conf_pass = tk.StringVar()

        tk.Label(adm_card, text="Admin Display Name:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(4, 2))
        ttk.Entry(adm_card, textvariable=adm_fullname).pack(fill="x")

        tk.Label(adm_card, text="Current Password (Required to change password):", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(8, 2))
        ttk.Entry(adm_card, textvariable=old_pass, show="●").pack(fill="x")

        tk.Label(adm_card, text="New Password:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(8, 2))
        ttk.Entry(adm_card, textvariable=new_pass, show="●").pack(fill="x")

        tk.Label(adm_card, text="Confirm New Password:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w", pady=(8, 2))
        ttk.Entry(adm_card, textvariable=conf_pass, show="●").pack(fill="x")

        def update_admin():
            conn = self.db.connect()
            cur = conn.cursor()
            cur.execute("UPDATE admin SET full_name=? WHERE id=?", (adm_fullname.get().strip(), self.admin_user["id"]))
            self.admin_user["full_name"] = adm_fullname.get().strip()

            if new_pass.get():
                stored_hash = cur.execute("SELECT password_hash FROM admin WHERE id=?", (self.admin_user["id"],)).fetchone()[0]
                if self.db.hash_password(old_pass.get()) != stored_hash:
                    conn.close()
                    messagebox.showerror("Error", "Current password is incorrect!")
                    return
                if new_pass.get() != conf_pass.get():
                    conn.close()
                    messagebox.showerror("Error", "New passwords do not match!")
                    return
                cur.execute("UPDATE admin SET password_hash=? WHERE id=?", (self.db.hash_password(new_pass.get()), self.admin_user["id"]))

            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Admin profile & credentials updated!")

        tk.Button(adm_card, text="🔄 Update Profile & Password", bg=COLORS["purple"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, pady=8, command=update_admin).pack(fill="x", pady=14)

        db_card = tk.Frame(grid, bg="white", padx=18, pady=18, highlightbackground=COLORS["border"], highlightthickness=1)
        db_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        tk.Label(db_card, text="🗄️ SQLite Database Backup & Restore", font=("Segoe UI", 12, "bold"), bg="white", fg=COLORS["text_dark"]).pack(anchor="w")
        tk.Label(db_card, text="Create a full backup of all student, teacher, attendance, exam, and fee records, or restore from a previous backup.", font=("Segoe UI", 9), bg="white", fg=COLORS["text_muted"]).pack(anchor="w", pady=(2, 12))

        def backup_db():
            dest = filedialog.asksaveasfilename(
                defaultextension=".db",
                initialfile=f"backup_school_db_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                filetypes=[("SQLite Database", "*.db")]
            )
            if dest:
                shutil.copy(DB_NAME, dest)
                messagebox.showinfo("Backup Complete", f"Database successfully backed up to:\n{dest}")

        def restore_db():
            src = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db")])
            if src and messagebox.askyesno("Confirm Restore", "Restoring will overwrite all current data with the backup file. Continue?"):
                shutil.copy(src, DB_NAME)
                messagebox.showinfo("Restored", "Database restored successfully! Reloading dashboard...")
                self.switch_page("dashboard")

        db_btns = tk.Frame(db_card, bg="white")
        db_btns.pack(anchor="w")
        tk.Button(db_btns, text="⬇️ Backup Database (.db)", bg=COLORS["primary"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=backup_db).pack(side="left", padx=(0, 12))
        tk.Button(db_btns, text="⬆️ Restore Database (.db)", bg=COLORS["warning"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=restore_db).pack(side="left")


# ==============================================================================
# APPLICATION ENTRY POINT
# ==============================================================================
def main():
    root = tk.Tk()
    db = DatabaseManager()

    def start_dashboard(admin_user):
        StudentManagementApp(root, db, admin_user, on_logout=show_login)

    def show_login():
        LoginWindow(root, db, on_login_success=start_dashboard)

    show_login()
    root.mainloop()


if __name__ == "__main__":
    main()