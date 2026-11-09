import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime
from utils.validation import (
    validate_mark_value,
    validate_semester_value,
    validate_email_value,
    validate_student_id_value,
    validate_student_record,
    normalize_headers,
)

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
    """Enrolls a new student with strict validation."""
    validate_student_record(name, email, department, semester)
    clean_email = validate_email_value(email, required=False)
    clean_sem = validate_semester_value(semester)
    clean_name = str(name).strip()
    clean_dept = str(department).strip()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (name, email, department, semester)
            VALUES (?, ?, ?, ?)
        """, (clean_name, clean_email, clean_dept, clean_sem))
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
    """Updates student demographic data with strict validation."""
    clean_id = validate_student_id_value(student_id)
    if not clean_id:
        raise ValueError("Invalid student ID for update.")
    validate_student_record(name, email, department, semester)
    clean_email = validate_email_value(email, required=False)
    clean_sem = validate_semester_value(semester)
    clean_name = str(name).strip()
    clean_dept = str(department).strip()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students
            SET name = ?, email = ?, department = ?, semester = ?
            WHERE id = ?
        """, (clean_name, clean_email, clean_dept, clean_sem, clean_id))
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
    """Saves or updates subject marks with range and data-type validation."""
    clean_id = validate_student_id_value(student_id)
    if not clean_id:
        raise ValueError(f"Student ID '{student_id}' must be a positive integer.")
    clean_exam_id = validate_student_id_value(exam_id) if exam_id is not None else 1
    if not clean_exam_id:
        raise ValueError(f"Exam ID '{exam_id}' must be a positive integer.")
    if not subject or not str(subject).strip():
        raise ValueError("Subject name cannot be empty.")
    clean_subject = str(subject).strip()
    clean_marks = validate_mark_value(marks)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM marks
        WHERE student_id = ? AND subject = ? AND exam_id = ?
    """, (clean_id, clean_subject, clean_exam_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE marks SET marks = ? WHERE id = ?
        """, (clean_marks, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO marks (student_id, subject, marks, exam_id)
            VALUES (?, ?, ?, ?)
        """, (clean_id, clean_subject, clean_marks, clean_exam_id))
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
# Data Import from CSV & DataFrame
# ---------------------------------------------------------

def import_student_dataframe(df, overwrite=False, allow_updates=False):
    """
    Consolidated atomic import pipeline for student profiles and marks.
    Enforces:
    - Canonical column header mapping with duplicate header detection.
    - Semester validation (strictly integer between 1 and 12).
    - Email regex format validation.
    - Strict positive integer Student_ID validation (rejects decimals/floats like 22.5, zeros, negatives).
    - Append mode safety: if overwrite=False and allow_updates=False,
      conflicts with existing database records are rejected with descriptive ValueError.
    - If allow_updates=True, updates matching records.
    - If overwrite=True, safely purges existing tables in foreign-key order.
    - Atomic transaction rollback on any exception.
    """
    if df.empty:
        raise ValueError("Cannot import an empty dataset.")

    canonical_map = {
        "name": "Name", "student_name": "Name", "studentname": "Name", "full_name": "Name", "fullname": "Name",
        "department": "Department", "dept": "Department", "branch": "Department", "stream": "Department",
        "semester": "Semester", "sem": "Semester", "term": "Semester",
        "email": "Email", "e-mail": "Email", "email_id": "Email", "mail": "Email",
        "id": "Student_ID", "student_id": "Student_ID", "studentid": "Student_ID", "roll_no": "Student_ID", "rollno": "Student_ID",
    }

    renamed = {}
    normalized_list = []
    for col in df.columns:
        c_clean = str(col).strip().replace("*", "").replace("#", "")
        c_lower = c_clean.lower().replace(" ", "_").replace("-", "_")
        target_name = canonical_map.get(c_lower, c_clean)
        renamed[col] = target_name
        normalized_list.append(target_name)

    # Detect duplicate columns after normalization
    counts = pd.Series(normalized_list).value_counts()
    dup_cols = counts[counts > 1].index.tolist()
    if dup_cols:
        raise ValueError(f"Duplicate column headers detected after normalization: {', '.join(dup_cols)}.")

    work_df = df.rename(columns=renamed).copy()

    if "Name" not in work_df.columns:
        raise ValueError("Dataset must contain a student 'Name' column.")

    subjects = [col for col in work_df.columns if col not in ["Name", "Department", "Semester", "Email", "Student_ID"]]
    if not subjects:
        raise ValueError("No subject score columns detected in dataset.")

    # Validate Names
    for idx, name_val in work_df["Name"].items():
        s_name = str(name_val).strip() if pd.notna(name_val) else ""
        if not s_name or s_name.lower() in ["nan", "null", "none", ""]:
            raise ValueError(f"Row {idx + 1}: Empty or invalid student name.")
        if len(s_name) < 2:
            raise ValueError(f"Row {idx + 1}: Student name too short.")

    # Validate Semesters strictly 1-12
    if "Semester" in work_df.columns:
        for idx, sem_val in work_df["Semester"].items():
            try:
                validate_semester_value(sem_val)
            except ValueError as ve:
                raise ValueError(f"Row {idx + 1}: {ve}")

    # Validate Email format
    if "Email" in work_df.columns:
        for idx, em_val in work_df["Email"].items():
            if pd.notna(em_val) and str(em_val).strip() not in ["", "nan", "none", "null"]:
                try:
                    validate_email_value(em_val)
                except ValueError as ve:
                    raise ValueError(f"Row {idx + 1}: {ve}")

    # Validate Student_ID values strictly if present (reject floats like 22.5, 0, negative)
    if "Student_ID" in work_df.columns:
        for idx, id_val in work_df["Student_ID"].items():
            if pd.notna(id_val) and str(id_val).strip() not in ["", "nan", "none", "null"]:
                try:
                    validate_student_id_value(id_val)
                except ValueError as ve:
                    raise ValueError(f"Row {idx + 1}: {ve}")

    # Validate numeric marks [0, 100]
    for sub in subjects:
        for idx, m_val in work_df[sub].items():
            try:
                validate_mark_value(m_val)
            except ValueError as ve:
                raise ValueError(f"Row {idx + 1}: {ve} in subject '{sub}'.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if overwrite:
            cursor.execute("DELETE FROM attendance")
            cursor.execute("DELETE FROM marks")
            cursor.execute("DELETE FROM students")

        processed_count = 0
        for _, row in work_df.iterrows():
            s_name = str(row["Name"]).strip()
            dept = str(row["Department"]).strip() if "Department" in work_df.columns and pd.notna(row["Department"]) and str(row["Department"]).strip() != "" else "BCA"
            sem = validate_semester_value(row["Semester"]) if "Semester" in work_df.columns and pd.notna(row["Semester"]) else 3
            email = validate_email_value(row["Email"]) if "Email" in work_df.columns and pd.notna(row["Email"]) else None

            given_id = None
            if "Student_ID" in work_df.columns and pd.notna(row["Student_ID"]):
                given_id = validate_student_id_value(row["Student_ID"])

            student_id = None
            conflict_reason = None
            if not overwrite:
                if given_id is not None:
                    cursor.execute("SELECT id, name FROM students WHERE id = ?", (given_id,))
                    match = cursor.fetchone()
                    if match:
                        student_id = match[0]
                        conflict_reason = f"Student ID {given_id} already exists (enrolled as '{match[1]}')"

                if student_id is None and email:
                    cursor.execute("SELECT id, name FROM students WHERE LOWER(email) = LOWER(?)", (email,))
                    match = cursor.fetchone()
                    if match:
                        student_id = match[0]
                        conflict_reason = f"Email '{email}' already exists (enrolled as '{match[1]}')"

                if student_id is None:
                    cursor.execute("SELECT id FROM students WHERE LOWER(name) = LOWER(?) AND LOWER(department) = LOWER(?)", (s_name, dept))
                    match = cursor.fetchone()
                    if match:
                        student_id = match[0]
                        conflict_reason = f"Student '{s_name}' in department '{dept}' already exists (ID: {match[0]})"

                if student_id is not None and not allow_updates:
                    raise ValueError(
                        f"Row {processed_count + 1}: Conflict detected - {conflict_reason}. "
                        "In Append mode, existing records are protected from silent overwriting. "
                        "To update existing records, choose 'Update Existing Records', or select 'Overwrite Database' with explicit confirmation."
                    )

            if student_id is not None:
                cursor.execute("""
                    UPDATE students
                    SET name = ?, email = COALESCE(?, email), department = ?, semester = ?
                    WHERE id = ?
                """, (s_name, email, dept, sem, student_id))
            else:
                if given_id is not None:
                    cursor.execute("SELECT id FROM students WHERE id = ?", (given_id,))
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO students (id, name, email, department, semester)
                            VALUES (?, ?, ?, ?, ?)
                        """, (given_id, s_name, email, dept, sem))
                        student_id = given_id
                    else:
                        cursor.execute("""
                            INSERT INTO students (name, email, department, semester)
                            VALUES (?, ?, ?, ?)
                        """, (s_name, email, dept, sem))
                        student_id = cursor.lastrowid
                else:
                    cursor.execute("""
                        INSERT INTO students (name, email, department, semester)
                        VALUES (?, ?, ?, ?)
                    """, (s_name, email, dept, sem))
                    student_id = cursor.lastrowid

            for subject in subjects:
                score = validate_mark_value(row[subject])
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
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def import_students_from_csv(file_path, overwrite=False, allow_updates=False):
    """Safely imports student records and subject marks from a CSV file."""
    df = pd.read_csv(file_path)
    return import_student_dataframe(df, overwrite=overwrite, allow_updates=allow_updates)


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
