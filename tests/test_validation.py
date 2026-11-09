import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from utils.validation import (
    validate_student_dataframe,
    validate_marks_dataframe,
    validate_student_record,
)


def test_valid_student_record():
    """Verify valid record passes without exception."""
    validate_student_record("John Doe", "john@example.com", "BCA", 3)


def test_invalid_student_record_empty_name():
    """Verify empty name raises ValueError."""
    try:
        validate_student_record("", "john@example.com", "BCA", 3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_invalid_student_record_email():
    """Verify malformed email raises ValueError."""
    try:
        validate_student_record("John", "invalid_email", "BCA", 3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_invalid_semester():
    """Verify out-of-range semester raises ValueError."""
    try:
        validate_student_record("John", "john@example.com", "BCA", 15)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    print("Running validation tests...")
    test_valid_student_record()
    test_invalid_student_record_empty_name()
    test_invalid_student_record_email()
    test_invalid_semester()
    print("Validation tests passed successfully.")
