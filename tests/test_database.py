import sys
import os
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database


class TestDatabase(unittest.TestCase):
    def test_database_connection_and_tables(self):
        """Verify tables exist and foreign keys are active."""
        database.create_tables()
        conn = database.get_connection()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        self.assertEqual(fk, 1, "Foreign keys must be enabled in SQLite connection.")

        students = database.get_students()
        self.assertIsInstance(students, pd.DataFrame)
        self.assertFalse(students.empty)
        self.assertIn("name", students.columns)

    def test_marks_retrieval(self):
        """Verify marks table returns proper schema."""
        marks = database.get_marks()
        self.assertIsInstance(marks, pd.DataFrame)
        self.assertFalse(marks.empty)
        self.assertIn("marks", marks.columns)
        self.assertIn("student_id", marks.columns)
        self.assertIn("id", marks.columns)

    def test_examinations_table(self):
        """Verify examinations are seeded."""
        exams = database.get_examinations()
        self.assertIsInstance(exams, pd.DataFrame)
        self.assertGreaterEqual(len(exams), 4)

    def test_attendance_summary_unrecorded_logic(self):
        """Verify students without attendance are flagged as Not Recorded and not assigned arbitrary values."""
        database.add_student("Temp Check", "temp_att_check@example.com", "BCA", 3)
        stds = database.get_students()
        temp_id = int(stds[stds["email"] == "temp_att_check@example.com"].iloc[0]["id"])

        att = database.get_attendance_summary()
        temp_att = att[att["student_id"] == temp_id].iloc[0]

        self.assertEqual(temp_att["attendance_status"], "Not Recorded")
        self.assertTrue(pd.isna(temp_att["attendance_percentage"]))

        database.delete_student(temp_id)

    def test_safe_import_protects_records(self):
        """Verify safe CSV import does not wipe existing students when overwrite=False."""
        initial_count = len(database.get_students())
        self.assertGreater(initial_count, 0)

        imported = database.import_students_from_csv("data/students.csv", overwrite=False)
        self.assertGreater(imported, 0)

        after_count = len(database.get_students())
        self.assertGreaterEqual(after_count, initial_count, "Existing records must be preserved.")


if __name__ == "__main__":
    unittest.main()
