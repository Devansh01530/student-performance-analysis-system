import sys
import os
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.validation import (
    validate_student_record,
    validate_student_dataframe,
    validate_marks_dataframe,
)


class TestValidation(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
