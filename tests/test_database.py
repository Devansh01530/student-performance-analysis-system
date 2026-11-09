import sys
import os
import unittest
import tempfile
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Creates an isolated temporary SQLite database fixture for every test."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        database.create_tables()

    def tearDown(self):
        """Restores original database path and wipes the temporary test fixture."""
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_database_connection_and_tables(self):
        """Verify tables exist and foreign keys are active in isolated fixture."""
        conn = database.get_connection()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        self.assertEqual(fk, 1, "Foreign keys must be enabled in SQLite connection.")

        # Enroll test student
        database.add_student("Isolated Student", "isolated@example.com", "BCA", 3)
        students = database.get_students()
        self.assertIsInstance(students, pd.DataFrame)
        self.assertFalse(students.empty)
        self.assertIn("name", students.columns)
        self.assertEqual(students.iloc[0]["name"], "Isolated Student")

    def test_marks_retrieval(self):
        """Verify marks table returns proper schema in isolated fixture."""
        database.add_student("Marks Student", "marks@example.com", "BCA", 3)
        students = database.get_students()
        s_id = int(students.iloc[0]["id"])
        database.save_marks(s_id, "Python", 88.5, exam_id=1)

        marks = database.get_marks()
        self.assertIsInstance(marks, pd.DataFrame)
        self.assertFalse(marks.empty)
        self.assertIn("marks", marks.columns)
        self.assertIn("student_id", marks.columns)
        self.assertIn("id", marks.columns)
        self.assertEqual(float(marks.iloc[0]["marks"]), 88.5)

    def test_examinations_table(self):
        """Verify examinations are seeded in new database."""
        exams = database.get_examinations()
        self.assertIsInstance(exams, pd.DataFrame)
        self.assertGreaterEqual(len(exams), 4)

    def test_attendance_summary_unrecorded_logic(self):
        """Verify students without attendance are flagged as Not Recorded in isolated fixture."""
        database.add_student("Zero Att Student", "zero_att@example.com", "BCA", 3)
        stds = database.get_students()
        temp_id = int(stds[stds["email"] == "zero_att@example.com"].iloc[0]["id"])

        att = database.get_attendance_summary()
        temp_att = att[att["student_id"] == temp_id].iloc[0]

        self.assertEqual(temp_att["attendance_status"], "Not Recorded")
        self.assertTrue(pd.isna(temp_att["attendance_percentage"]))

    def test_safe_import_protects_records(self):
        """Verify safe CSV import does not wipe existing students when overwrite=False."""
        database.add_student("Existing Protected", "protected@example.com", "BCA", 3)
        initial_count = len(database.get_students())
        self.assertEqual(initial_count, 1)

        # Import baseline CSV in safe append mode
        imported = database.import_students_from_csv("data/students.csv", overwrite=False)
        self.assertGreater(imported, 0)

        after_students = database.get_students()
        self.assertGreater(len(after_students), initial_count)
        # Check that protected student still exists
        self.assertTrue((after_students["email"] == "protected@example.com").any())

    def test_save_marks_range_validation(self):
        """Verify save_marks enforces 0-100 numeric boundaries."""
        database.add_student("Bounds Student", "bounds@example.com", "BCA", 3)
        stds = database.get_students()
        b_id = int(stds[stds["email"] == "bounds@example.com"].iloc[0]["id"])

        # Above 100
        with self.assertRaises(ValueError):
            database.save_marks(b_id, "Python", 105.0)

        # Below 0
        with self.assertRaises(ValueError):
            database.save_marks(b_id, "Python", -10.0)

        # Non-numeric string
        with self.assertRaises(ValueError):
            database.save_marks(b_id, "Python", "abc")

        # Valid mark
        database.save_marks(b_id, "Python", 85.5)
        m = database.get_marks(student_id=b_id)
        self.assertEqual(float(m.iloc[0]["marks"]), 85.5)

    def test_append_mode_conflict_rejection(self):
        """Verify append mode rejects conflicts instead of silently updating existing records."""
        database.add_student("Conflict Test", "conflict@example.com", "BCA", 3)

        conflict_df = pd.DataFrame({
            "Name": ["Conflict Test"],
            "Department": ["BCA"],
            "Semester": [3],
            "Email": ["conflict@example.com"],
            "Python": [75],
        })

        # Append mode should raise ValueError on existing conflict
        with self.assertRaises(ValueError) as ctx:
            database.import_student_dataframe(conflict_df, overwrite=False, allow_updates=False)
        self.assertIn("Conflict detected", str(ctx.exception))

    def test_update_mode_allows_updates(self):
        """Verify allow_updates=True successfully refreshes existing student records."""
        database.add_student("Update Target", "update@example.com", "BCA", 3)

        update_df = pd.DataFrame({
            "Name": ["Update Target"],
            "Department": ["BCA"],
            "Semester": [4],
            "Email": ["update@example.com"],
            "Python": [95],
        })

        imported = database.import_student_dataframe(update_df, overwrite=False, allow_updates=True)
        self.assertEqual(imported, 1)

        stds = database.get_students()
        updated_row = stds[stds["email"] == "update@example.com"].iloc[0]
        self.assertEqual(int(updated_row["semester"]), 4)

    def test_reject_decimal_student_id_in_import(self):
        """Verify fractional/decimal student IDs are strictly rejected."""
        bad_id_df = pd.DataFrame({
            "Student_ID": [22.5],
            "Name": ["Decimal ID"],
            "Semester": [3],
            "Python": [80],
        })
        with self.assertRaises(ValueError):
            database.import_student_dataframe(bad_id_df)

    def test_cascade_deletion(self):
        """Verify foreign key cascading safely removes related marks and attendance."""
        database.add_student("Cascade Target", "cascade@example.com", "BCA", 3)
        stds = database.get_students()
        c_id = int(stds[stds["email"] == "cascade@example.com"].iloc[0]["id"])

        database.save_marks(c_id, "Python", 92.0, exam_id=1)
        database.record_attendance(c_id, "Python", "2026-10-20", "Present")

        self.assertEqual(len(database.get_marks(student_id=c_id)), 1)
        self.assertEqual(len(database.get_attendance(student_id=c_id)), 1)

        # Delete student
        database.delete_student(c_id)

        # Verify cascade removed marks and attendance
        self.assertEqual(len(database.get_marks(student_id=c_id)), 0)
        self.assertEqual(len(database.get_attendance(student_id=c_id)), 0)


if __name__ == "__main__":
    unittest.main()
