import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime

# Database location
DB_PATH = os.path.join("data", "students.db")


def get_connection(db_path=None):
    """Returns a connection to the SQLite database with foreign keys enabled."""
    target_path = db_path or DB_PATH
    dir_name = os.path.dirname(target_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables():
    """
    Creates and upgrades all required database tables.
    Maintains referential integrity and backward compatibility.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            department TEXT,
            semester INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Examinations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS examinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            exam_date TEXT,
            exam_type TEXT
        )
    """)

    # 3. Marks Table (supports exam_id for multi-examination progress tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT NOT NULL,
            marks REAL NOT NULL,
            exam_id INTEGER DEFAULT 1,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (exam_id) REFERENCES examinations(id),
            UNIQUE(student_id, subject, exam_id)
        )
    """)

    # Schema migration: Ensure exam_id exists in existing marks table
    cursor.execute("PRAGMA table_info(marks)")
    marks_cols = [c[1] for c in cursor.fetchall()]
    if "exam_id" not in marks_cols:
        cursor.execute("ALTER TABLE marks ADD COLUMN exam_id INTEGER DEFAULT 1")

    # 4. Attendance Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, subject, attendance_date)
        )
    """)

    # 5. Departments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # 6. Subjects Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)

    conn.commit()

    # Seed core reference data if not present
    _seed_initial_reference_data(cursor)

    conn.commit()
    conn.close()


def _seed_initial_reference_data(cursor):
    """Populates standard examinations, departments, and default subjects if absent."""
    # Seed Examinations
    default_exams = [
        ("Internal Assessment 1", "2026-09-15", "Internal"),
        ("Internal Assessment 2", "2026-10-20", "Internal"),
        ("Mid-Semester Examination", "2026-11-05", "Mid-Term"),
        ("Final Examination", "2026-12-10", "Final"),
    ]
    for exam_name, exam_date, exam_type in default_exams:
        cursor.execute("""
            INSERT OR IGNORE INTO examinations (name, exam_date, exam_type)
            VALUES (?, ?, ?)
        """, (exam_name, exam_date, exam_type))

    # Seed Departments
    default_departments = ["BCA", "B.Tech CSE", "B.Sc IT", "MCA"]
    for dept in default_departments:
        cursor.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (dept,))

    # Seed Subjects
    default_subjects = [
        ("Python", 1),
        ("C++", 1),
        ("Java", 1),
        ("Data Structures", 1),
        ("Database Management", 1),
    ]
    for sub, d_id in default_subjects:
        cursor.execute("INSERT OR IGNORE INTO subjects (name, department_id) VALUES (?, ?)", (sub, d_id))


# ---------------------------------------------------------
# Student Operations
# ---------------------------------------------------------

def add_student(name, email, department, semester):
    """Enrolls a new student."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (name, email, department, semester)
            VALUES (?, ?, ?, ?)
        """, (name, email, department, semester))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_students():
    """Returns all students as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM students ORDER BY id", conn)
    conn.close()
    return df


def update_student(student_id, name, email, department, semester):
    """Updates student demographic data."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students
            SET name = ?, email = ?, department = ?, semester = ?
            WHERE id = ?
        """, (name, email, department, semester, student_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_student(student_id):
    """Deletes student and cascades through marks and attendance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM marks WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------
# Marks Operations
# ---------------------------------------------------------

def save_marks(student_id, subject, marks, exam_id=1):
    """Saves or updates subject marks for a given examination."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM marks
        WHERE student_id = ? AND subject = ? AND exam_id = ?
    """, (student_id, subject, exam_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE marks SET marks = ? WHERE id = ?
        """, (marks, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO marks (student_id, subject, marks, exam_id)
            VALUES (?, ?, ?, ?)
        """, (student_id, subject, marks, exam_id))
    conn.commit()
    conn.close()


def get_marks(exam_id=None, student_id=None):
    """
    Returns student marks joined with student metadata.
    Supports optional filtering by exam_id and/or student_id.
    Always includes both 'id' and 'student_id' columns.
    """
    conn = get_connection()
    query = """
        SELECT
            students.id,
            students.id AS student_id,
            students.name,
            students.department,
            students.semester,
            marks.subject,
            marks.marks,
            marks.exam_id,
            examinations.name AS exam_name
        FROM students
        JOIN marks ON students.id = marks.student_id
        LEFT JOIN examinations ON marks.exam_id = examinations.id
        WHERE 1=1
    """
    params = []
    if exam_id is not None:
        query += " AND marks.exam_id = ?"
        params.append(exam_id)
    if student_id is not None:
        query += " AND marks.student_id = ?"
        params.append(student_id)

    query += " ORDER BY students.name, marks.subject"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# ---------------------------------------------------------
# Examinations & Progress Operations
# ---------------------------------------------------------

def get_examinations():
    """Returns all registered examinations."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM examinations ORDER BY id", conn)
    conn.close()
    return df


def add_examination(name, exam_date, exam_type):
    """Creates a new examination."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO examinations (name, exam_date, exam_type)
            VALUES (?, ?, ?)
        """, (name, exam_date, exam_type))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_all_exam_progress():
    """Returns marks across all examinations for progress tracking."""
    conn = get_connection()
    query = """
        SELECT
            students.id AS student_id,
            students.name,
            students.department,
            students.semester,
            examinations.id AS exam_id,
            examinations.name AS exam_name,
            examinations.exam_date,
            marks.subject,
            marks.marks
        FROM marks
        JOIN students ON marks.student_id = students.id
        JOIN examinations ON marks.exam_id = examinations.id
        ORDER BY students.name, examinations.id, marks.subject
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ---------------------------------------------------------
# Attendance Operations
# ---------------------------------------------------------

def record_attendance(student_id, subject, attendance_date, status):
    """Records daily attendance status ('Present' or 'Absent')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM attendance
        WHERE student_id = ? AND subject = ? AND attendance_date = ?
    """, (student_id, subject, attendance_date))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO attendance (student_id, subject, attendance_date, status)
            VALUES (?, ?, ?, ?)
        """, (student_id, subject, attendance_date, status))
    conn.commit()
    conn.close()


def get_attendance(student_id=None, subject=None, date=None):
    """Fetches attendance records with optional filtering."""
    conn = get_connection()
    query = """
        SELECT
            attendance.id,
            attendance.student_id,
            students.name,
            students.department,
            students.semester,
            attendance.subject,
            attendance.attendance_date,
            attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        WHERE 1=1
    """
    params = []
    if student_id:
        query += " AND attendance.student_id = ?"
        params.append(student_id)
    if subject and subject != "All":
        query += " AND attendance.subject = ?"
        params.append(subject)
    if date:
        query += " AND attendance.attendance_date = ?"
        params.append(date)

    query += " ORDER BY attendance.attendance_date DESC, students.name ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_attendance_summary(before_date=None):
    """
    Calculates attendance statistics per student.
    If before_date is provided, strictly filters attendance logs to attendance_date <= before_date.
    This prevents future attendance records from leaking into historical ML prediction evaluations.
    """
    conn = get_connection()
    if before_date:
        query = """
            SELECT
                students.id AS student_id,
                students.name,
                students.department,
                students.semester,
                COUNT(attendance.id) AS total_classes,
                SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) AS classes_attended
            FROM students
            LEFT JOIN attendance ON students.id = attendance.student_id AND attendance.attendance_date <= ?
            GROUP BY students.id, students.name, students.department, students.semester
            ORDER BY students.id
        """
        df = pd.read_sql_query(query, conn, params=[before_date])
    else:
        query = """
            SELECT
                students.id AS student_id,
                students.name,
                students.department,
                students.semester,
                COUNT(attendance.id) AS total_classes,
                SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) AS classes_attended
            FROM students
            LEFT JOIN attendance ON students.id = attendance.student_id
            GROUP BY students.id, students.name, students.department, students.semester
            ORDER BY students.id
        """
        df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    df["classes_attended"] = df["classes_attended"].fillna(0).astype(int)
    df["total_classes"] = df["total_classes"].fillna(0).astype(int)

    def calc_pct(row):
        if row["total_classes"] == 0:
            return None
        return round((row["classes_attended"] / row["total_classes"]) * 100, 2)

    def calc_status(row):
        if row["total_classes"] == 0:
            return "Not Recorded"
        pct = (row["classes_attended"] / row["total_classes"]) * 100
        return "Normal" if pct >= 75.0 else "Low Attendance"

    df["attendance_percentage"] = df.apply(calc_pct, axis=1)
    df["attendance_status"] = df.apply(calc_status, axis=1)
    return df


def get_historical_attendance_summary(before_date):
    """Convenience alias for get_attendance_summary(before_date)."""
    return get_attendance_summary(before_date=before_date)


# ---------------------------------------------------------
# Departments and Subjects
# ---------------------------------------------------------

def get_departments():
    """Returns all departments."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM departments ORDER BY name", conn)
    conn.close()
    return df


def get_subjects(department_id=None):
    """Returns subjects, optionally filtered by department."""
    conn = get_connection()
    query = "SELECT * FROM subjects"
    params = []
    if department_id:
        query += " WHERE department_id = ?"
        params.append(department_id)
    query += " ORDER BY name"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# ---------------------------------------------------------
# Data Import from CSV
# ---------------------------------------------------------

def import_students_from_csv(file_path, overwrite=False):
    """
    Safely imports student records and subject marks from a CSV file.
    - Standardizes and normalizes column headers (case-insensitive metadata mapping).
    - If overwrite is False (default): preserves existing students and attendance,
      inserting only new students or updating marks for existing students.
    - If overwrite is True: safely deletes in foreign-key order (attendance -> marks -> students)
      and resets the database tables cleanly.
    """
    df = pd.read_csv(file_path)
    
    canonical_map = {
        "name": "Name", "student_name": "Name", "studentname": "Name", "full_name": "Name",
        "department": "Department", "dept": "Department", "branch": "Department",
        "semester": "Semester", "sem": "Semester", "term": "Semester",
        "email": "Email", "e-mail": "Email", "email_id": "Email",
        "id": "Student_ID", "student_id": "Student_ID", "roll_no": "Student_ID",
    }
    renamed = {}
    for col in df.columns:
        c_clean = str(col).strip().replace("*", "").replace("#", "")
        c_lower = c_clean.lower().replace(" ", "_").replace("-", "_")
        renamed[col] = canonical_map.get(c_lower, c_clean)
    df = df.rename(columns=renamed)

    if "Name" not in df.columns:
        raise ValueError("CSV must contain a 'Name' column.")

    subjects = [col for col in df.columns if col not in ["Name", "Department", "Semester", "Email", "Student_ID"]]
    if not subjects:
        raise ValueError("No subject columns detected in file.")

    for subject in subjects:
        df[subject] = pd.to_numeric(df[subject], errors="coerce")

    if df["Name"].isna().any() or df[subjects].isna().any().any():
        raise ValueError("CSV contains missing or invalid student data.")

    if ((df[subjects] < 0) | (df[subjects] > 100)).any().any():
        raise ValueError("Marks must be between 0 and 100.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if overwrite:
            # Clean up all related tables in foreign-key referential order
            cursor.execute("DELETE FROM attendance")
            cursor.execute("DELETE FROM marks")
            cursor.execute("DELETE FROM students")

        processed_count = 0
        for _, row in df.iterrows():
            s_name = str(row["Name"]).strip()
            dept = str(row["Department"]).strip() if "Department" in df.columns and pd.notna(row["Department"]) else "BCA"
            sem = int(row["Semester"]) if "Semester" in df.columns and pd.notna(row["Semester"]) else 3
            email = str(row["Email"]).strip() if "Email" in df.columns and pd.notna(row["Email"]) and str(row["Email"]).strip() != "" else None

            student_id = None
            if not overwrite:
                # Check for existing student
                if email:
                    cursor.execute("SELECT id FROM students WHERE email = ?", (email,))
                    match = cursor.fetchone()
                    if match:
                        student_id = match[0]
                if student_id is None:
                    cursor.execute("SELECT id FROM students WHERE name = ? AND department = ?", (s_name, dept))
                    match = cursor.fetchone()
                    if match:
                        student_id = match[0]

            if student_id is None:
                cursor.execute("""
                    INSERT INTO students (name, email, department, semester)
                    VALUES (?, ?, ?, ?)
                """, (s_name, email, dept, sem))
                student_id = cursor.lastrowid

            for subject in subjects:
                score = float(row[subject])
                cursor.execute("""
                    SELECT id FROM marks
                    WHERE student_id = ? AND subject = ? AND exam_id = 1
                """, (student_id, subject))
                m_existing = cursor.fetchone()
                if m_existing:
                    cursor.execute("UPDATE marks SET marks = ? WHERE id = ?", (score, m_existing[0]))
                else:
                    cursor.execute("""
                        INSERT INTO marks (student_id, subject, marks, exam_id)
                        VALUES (?, ?, ?, 1)
                    """, (student_id, subject, score))

            processed_count += 1

        conn.commit()
        return processed_count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------
# Backup and Maintenance
# ---------------------------------------------------------

def backup_database(backup_dir="reports"):
    """Creates a timestamped snapshot copy of students.db."""
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"students_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, dest)
    return dest
