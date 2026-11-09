import sys
import os
import unittest
import tempfile
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import importlib
from utils.validation import (
    validate_student_record,
    validate_student_dataframe,
    validate_marks_dataframe,
)

data_import_mod = importlib.import_module("pages.10_Data_Import")
audit_and_validate_dataset = data_import_mod.audit_and_validate_dataset
normalize_headers = data_import_mod.normalize_headers


class TestValidation(unittest.TestCase):
    def setUp(self):
        """Creates an isolated temporary SQLite database fixture."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        database.create_tables()

    def tearDown(self):
        """Restores original database path and removes temporary fixture."""
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_valid_student_record(self):
        """Verify valid record passes without exception."""
        validate_student_record("John Doe", "john@example.com", "BCA", 3)

    def test_invalid_student_record_empty_name(self):
        """Verify empty name raises ValueError."""
        with self.assertRaises(ValueError):
            validate_student_record("", "john@example.com", "BCA", 3)

    def test_invalid_student_record_email(self):
        """Verify malformed email raises ValueError."""
        with self.assertRaises(ValueError):
            validate_student_record("John", "invalid_email", "BCA", 3)

    def test_invalid_semester(self):
        """Verify out-of-range semester raises ValueError."""
        with self.assertRaises(ValueError):
            validate_student_record("John", "john@example.com", "BCA", 15)
        with self.assertRaises(ValueError):
            validate_student_record("John", "john@example.com", "BCA", 0)

    def test_duplicate_column_headers_rejected(self):
        """Verify that files with columns mapping to the same canonical name are rejected."""
        # 'Name' and 'Student_Name' both map to 'Name'
        raw_df = pd.DataFrame({
            "Name": ["Aarav"],
            "Student_Name": ["Aarav Sharma"],
            "Python": [85],
        })
        norm_df = normalize_headers(raw_df)
        is_valid, errors, _ = audit_and_validate_dataset(norm_df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate" in e["Description"] for e in errors))

        with self.assertRaises(ValueError):
            database.import_student_dataframe(raw_df)

    def test_semester_strictly_between_1_and_12(self):
        """Verify semesters outside [1, 12] are rejected and not silently replaced."""
        bad_sem_df = pd.DataFrame({
            "Name": ["Student A", "Student B"],
            "Semester": [15, 0],
            "Python": [80, 85],
        })
        is_valid, errors, _ = audit_and_validate_dataset(bad_sem_df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Semester" in e["Column"] for e in errors))

        with self.assertRaises(ValueError):
            database.import_student_dataframe(bad_sem_df)

    def test_email_format_validation(self):
        """Verify invalid email strings are caught by validation."""
        bad_email_df = pd.DataFrame({
            "Name": ["Student X"],
            "Email": ["not-a-valid-email"],
            "Python": [90],
        })
        is_valid, errors, _ = audit_and_validate_dataset(bad_email_df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Email" in e["Column"] for e in errors))

        with self.assertRaises(ValueError):
            database.import_student_dataframe(bad_email_df)

    def test_database_atomic_rollback_on_error(self):
        """Verify that when an import error occurs mid-process, all changes are rolled back."""
        # Enroll an initial student
        database.add_student("Initial Safe", "safe@example.com", "BCA", 3)
        initial_students = len(database.get_students())
        initial_marks = len(database.get_marks())

        # Attempt to import a dataset where the second row has an out-of-range mark (150)
        faulty_df = pd.DataFrame({
            "Name": ["Good Student", "Bad Student"],
            "Semester": [3, 3],
            "Python": [85, 150],  # Out of range!
        })

        with self.assertRaises(ValueError):
            database.import_student_dataframe(faulty_df, overwrite=False)

        # Verify rollback preserved initial state and did NOT insert "Good Student" partially
        after_students = len(database.get_students())
        after_marks = len(database.get_marks())
        self.assertEqual(initial_students, after_students)
        self.assertEqual(initial_marks, after_marks)


if __name__ == "__main__":
    unittest.main()
