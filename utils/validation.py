'''utils/validation.py
Utility functions for validating data structures used by the Student Performance System.

The project currently stores data in two main tables (CSV/SQLite):
- ``students``: id, name, email, department, semester, created_at
- ``marks``:   id (student id), subject, marks

These helpers perform lightweight validation and raise ``ValueError`` with a clear message
when the input does not meet expectations. They are deliberately kept framework‑agnostic
so they can be used in the Streamlit UI, CLI scripts, and unit tests.
'''

import pandas as pd
from typing import Iterable

# ---------------------------------------------------------------------------
# Student Data validation
# ---------------------------------------------------------------------------

def validate_student_dataframe(df: pd.DataFrame) -> None:
    """Validate the ``students`` DataFrame.

    Expected columns: ``id``, ``name``, ``email``, ``department``, ``semester``.
    ``id`` must be integer, ``name`` non‑empty string, ``email`` either ``None`` or a
    valid e‑mail‑like string, ``semester`` integer in ``1..12``.
    Raises ``ValueError`` if any check fails.
    """
    required = {"id", "name", "email", "department", "semester"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Student DataFrame is missing columns: {missing}")

    # id must be integer and positive
    if not pd.api.types.is_integer_dtype(df["id"]):
        raise ValueError("Column 'id' must be of integer type")
    if (df["id"] <= 0).any():
        raise ValueError("Student IDs must be positive integers")

    # name non‑empty
    if df["name"].isnull().any() or (df["name"].str.strip() == "").any():
        raise ValueError("Student names cannot be empty")

    # email – allow NaN/None but if present must contain '@'
    email_series = df["email"].fillna("")
    if email_series.str.contains("@", regex=False).eq(False).any():
        # ignore empty strings (i.e., NaN) – only flag non‑empty invalid emails
        invalid = email_series[~email_series.str.contains("@", regex=False) & (email_series != "")]
        if not invalid.empty:
            raise ValueError(f"Invalid email addresses found: {invalid.tolist()}")

    # semester range check
    if not pd.api.types.is_integer_dtype(df["semester"]):
        raise ValueError("Column 'semester' must be integer")
    if not ((df["semester"] >= 1) & (df["semester"] <= 12)).all():
        raise ValueError("Semester must be between 1 and 12 inclusive")

# ---------------------------------------------------------------------------
# Marks Data validation
# ---------------------------------------------------------------------------

def validate_marks_dataframe(df: pd.DataFrame, allowed_subjects: Iterable[str] = None) -> None:
    """Validate the ``marks`` DataFrame.

    Expected columns: ``id`` (student id), ``subject``, ``marks``.
    ``marks`` must be numeric and within 0‑100.
    ``subject`` must be a non‑empty string and optionally belong to ``allowed_subjects``.
    """
    required = {"id", "subject", "marks"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Marks DataFrame is missing columns: {missing}")

    # id integer positive
    if not pd.api.types.is_integer_dtype(df["id"]):
        raise ValueError("Column 'id' in marks must be integer type")
    if (df["id"] <= 0).any():
        raise ValueError("Student IDs in marks must be positive integers")

    # subject non‑empty string
    if df["subject"].isnull().any() or (df["subject"].str.strip() == "").any():
        raise ValueError("Subject names cannot be empty")
    if allowed_subjects is not None:
        invalid_subjects = set(df["subject"]) - set(allowed_subjects)
        if invalid_subjects:
            raise ValueError(f"Found unexpected subjects: {invalid_subjects}")

    # marks numeric and 0‑100 inclusive
    if not pd.api.types.is_numeric_dtype(df["marks"]):
        raise ValueError("Column 'marks' must be numeric")
    if (df["marks"] < 0).any() or (df["marks"] > 100).any():
        raise ValueError("Marks must be between 0 and 100 inclusive")

# ---------------------------------------------------------------------------
# Helper used by the UI to validate before persisting
# ---------------------------------------------------------------------------

def validate_student_record(name: str, email: str, department: str, semester: int) -> None:
    """Validate individual student fields before insertion.

    Raises ``ValueError`` with a human‑readable message if any field is invalid.
    """
    if not name or not name.strip():
        raise ValueError("Student name cannot be empty")
    if email and "@" not in email:
        raise ValueError("Invalid email address")
    if not department or not department.strip():
        raise ValueError("Department cannot be empty")
    if not isinstance(semester, int) or not (1 <= semester <= 12):
        raise ValueError("Semester must be an integer between 1 and 12")

# ---------------------------------------------------------------------------
# Example usage (not executed on import)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simple sanity check when running the module directly
    import sys
    print("Running basic validation sanity check…")
    # Create tiny example frames
    students_df = pd.DataFrame({
        "id": [1],
        "name": ["Alice"],
        "email": ["alice@example.com"],
        "department": ["BCA"],
        "semester": [3],
    })
    marks_df = pd.DataFrame({
        "id": [1, 1],
        "subject": ["Python", "Java"],
        "marks": [85, 92],
    })
    try:
        validate_student_dataframe(students_df)
        validate_marks_dataframe(marks_df, allowed_subjects=["Python", "Java", "C++"])
        print("Validation passed successfully.")
    except Exception as exc:  # pragma: no cover
        print(f"Validation error: {exc}", file=sys.stderr)
        sys.exit(1)

