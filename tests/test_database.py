import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import pandas as pd


def test_database_connection_and_tables():
    """Verify tables exist and foreign keys are active."""
    database.create_tables()
    conn = database.get_connection()
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.close()
    assert fk == 1, "Foreign keys must be enabled in SQLite connection."

    students = database.get_students()
    assert isinstance(students, pd.DataFrame)
    assert not students.empty
    assert "name" in students.columns


def test_marks_retrieval():
    """Verify marks table returns proper schema."""
    marks = database.get_marks()
    assert isinstance(marks, pd.DataFrame)
    assert not marks.empty
    assert "marks" in marks.columns
    assert "student_id" in marks.columns
    assert "id" in marks.columns


def test_examinations_table():
    """Verify examinations are seeded."""
    exams = database.get_examinations()
    assert isinstance(exams, pd.DataFrame)
    assert len(exams) >= 4


def test_attendance_summary_unrecorded_logic():
    """Verify students without attendance are flagged as Not Recorded and not assigned an arbitrary 85%."""
    # Enroll temporary student with zero attendance logs
    database.add_student("Temp Check", "temp_att_check@example.com", "BCA", 3)
    stds = database.get_students()
    temp_id = int(stds[stds["email"] == "temp_att_check@example.com"].iloc[0]["id"])

    att = database.get_attendance_summary()
    temp_att = att[att["student_id"] == temp_id].iloc[0]

    assert temp_att["attendance_status"] == "Not Recorded"
    assert pd.isna(temp_att["attendance_percentage"])

    # Clean up
    database.delete_student(temp_id)


def test_safe_import_protects_records():
    """Verify safe CSV import does not wipe existing students when overwrite=False."""
    initial_count = len(database.get_students())
    assert initial_count > 0

    # Import baseline CSV in safe append mode
    imported = database.import_students_from_csv("data/students.csv", overwrite=False)
    assert imported > 0

    after_count = len(database.get_students())
    assert after_count >= initial_count, "Existing records must be preserved."


if __name__ == "__main__":
    print("Running database tests...")
    test_database_connection_and_tables()
    test_marks_retrieval()
    test_examinations_table()
    test_attendance_summary_unrecorded_logic()
    test_safe_import_protects_records()
    print("Database tests passed successfully.")
