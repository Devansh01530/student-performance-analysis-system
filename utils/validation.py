"""
utils/validation.py
Centralized validation and data normalization engine for the Student Performance System.

This module provides framework-agnostic validation functions and pre-commit audits:
- Canonical column header mapping with duplicate header detection
- Strict positive integer Student ID validation (rejecting decimals/floats, zeros, negatives)
- Semester validation (strictly integer between 1 and 12)
- Regex-based RFC 5322-compliant email validation
- Numeric subject marks validation strictly within [0.0, 100.0]
- Comprehensive pre-commit dataset auditing
- Record-level and DataFrame-level validators
"""

import re
import math
from typing import Iterable, Tuple, List, Dict, Any, Optional
import pandas as pd
import numpy as np

# RFC 5322 compliant simplified email regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Canonical metadata column mapping
CANONICAL_METADATA_MAP = {
    "name": "Name",
    "student_name": "Name",
    "studentname": "Name",
    "student name": "Name",
    "full_name": "Name",
    "fullname": "Name",
    "candidate_name": "Name",

    "department": "Department",
    "dept": "Department",
    "branch": "Department",
    "stream": "Department",
    "course": "Department",

    "semester": "Semester",
    "sem": "Semester",
    "term": "Semester",

    "email": "Email",
    "e-mail": "Email",
    "email_id": "Email",
    "emailid": "Email",
    "mail": "Email",

    "id": "Student_ID",
    "student_id": "Student_ID",
    "studentid": "Student_ID",
    "student id": "Student_ID",
    "roll_no": "Student_ID",
    "rollno": "Student_ID",
    "roll no": "Student_ID",
}


def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes and normalizes dataframe column headers into canonical metadata names.
    Removes leading/trailing whitespace, asterisks, and hashes,
    and maps case-insensitive variants to standard canonical names.
    """
    renamed = {}
    for col in df.columns:
        c_str = str(col).strip().replace("*", "").replace("#", "")
        c_key = c_str.lower().replace(" ", "_").replace("-", "_")
        target_name = CANONICAL_METADATA_MAP.get(c_key, c_str)
        renamed[col] = target_name
    return df.rename(columns=renamed)


def validate_student_id_value(val: Any) -> Optional[int]:
    """
    Validates a Student ID value.
    Must be a positive integer strictly greater than 0.
    Rejects decimals/floats (e.g. 22.5), negatives, zeros, and non-numeric strings.
    Returns the integer value, or None if val is null/empty.
    Raises ValueError on invalid format.
    """
    if val is None or pd.isna(val):
        return None

    # Handle float instances: reject fractional numbers like 22.5
    if isinstance(val, (float, np.floating)):
        if math.isnan(val):
            return None
        if not float(val).is_integer() or val <= 0:
            raise ValueError(f"Student ID '{val}' must be a positive integer without decimals.")
        return int(val)

    # Handle integer instances
    if isinstance(val, (int, np.integer)):
        if val <= 0:
            raise ValueError(f"Student ID '{val}' must be a positive integer greater than 0.")
        return int(val)

    # Handle string representations
    s = str(val).strip()
    if not s or s.lower() in ["nan", "none", "null"]:
        return None

    if "." in s:
        try:
            f = float(s)
            if not f.is_integer() or f <= 0:
                raise ValueError(f"Student ID '{val}' must be a positive integer without decimals.")
            return int(f)
        except (ValueError, TypeError):
            raise ValueError(f"Student ID '{val}' must be a positive integer.")

    if not s.isdigit() or int(s) <= 0:
        raise ValueError(f"Student ID '{val}' must be a positive integer greater than 0.")

    return int(s)


def validate_semester_value(val: Any) -> int:
    """
    Validates semester value.
    Must be an integer strictly between 1 and 12 inclusive.
    Rejects decimals (e.g. 2.5), out-of-range numbers, and non-numeric values.
    Returns valid integer semester.
    Raises ValueError on invalid semester.
    """
    if val is None or pd.isna(val):
        raise ValueError("Missing or null semester value.")

    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or not float(val).is_integer():
            raise ValueError(f"Semester '{val}' must be a valid integer between 1 and 12.")
        int_val = int(val)
        if not (1 <= int_val <= 12):
            raise ValueError(f"Semester '{val}' is outside the valid range [1, 12].")
        return int_val

    if isinstance(val, (int, np.integer)):
        if not (1 <= int(val) <= 12):
            raise ValueError(f"Semester '{val}' is outside the valid range [1, 12].")
        return int(val)

    s = str(val).strip()
    if "." in s:
        try:
            f = float(s)
            if not f.is_integer() or not (1 <= int(f) <= 12):
                raise ValueError(f"Semester '{val}' must be an integer between 1 and 12.")
            return int(f)
        except (ValueError, TypeError):
            raise ValueError(f"Semester '{val}' is not a valid integer between 1 and 12.")

    if not s.isdigit() or not (1 <= int(s) <= 12):
        raise ValueError(f"Semester '{val}' must be an integer between 1 and 12.")

    return int(s)


def validate_email_value(val: Any, required: bool = False) -> Optional[str]:
    """
    Validates an email address format using standard RFC pattern.
    If required=False, empty/null values return None.
    If non-empty, checks that email matches regex and returns trimmed lowercase email.
    Raises ValueError on invalid email format.
    """
    if val is None or pd.isna(val):
        if required:
            raise ValueError("Email address cannot be empty.")
        return None

    s = str(val).strip()
    if not s or s.lower() in ["nan", "none", "null"]:
        if required:
            raise ValueError("Email address cannot be empty.")
        return None

    if not EMAIL_REGEX.match(s):
        raise ValueError(f"Invalid email address format: '{val}'. Expected format user@domain.com.")

    return s.lower()


def validate_mark_value(val: Any) -> float:
    """
    Validates a student subject mark.
    Must be numeric and strictly between 0.0 and 100.0 inclusive.
    Rejects NaN, Inf, empty, or out-of-range values.
    Returns float rounded to 2 decimal places.
    Raises ValueError on invalid marks.
    """
    if val is None or pd.isna(val):
        raise ValueError("Mark cannot be empty or null.")

    try:
        f = float(val)
    except (ValueError, TypeError):
        raise ValueError(f"Non-numeric mark value: '{val}'.")

    if math.isnan(f) or math.isinf(f):
        raise ValueError(f"Invalid numeric mark value: '{val}'.")

    if f < 0.0 or f > 100.0:
        raise ValueError(f"Mark value '{f}' is outside the valid range [0.0, 100.0].")

    return round(f, 2)


def validate_student_record(name: str, email: Optional[str], department: str, semester: int) -> None:
    """
    Validates individual student fields before database insertion or update.
    Raises ValueError with a descriptive message if any field is invalid.
    """
    if not name or not str(name).strip():
        raise ValueError("Student name cannot be empty.")
    if len(str(name).strip()) < 2:
        raise ValueError("Student name too short (minimum 2 characters required).")

    if email is not None and str(email).strip() not in ["", "nan", "none", "null"]:
        validate_email_value(email, required=False)

    if not department or not str(department).strip():
        raise ValueError("Department cannot be empty.")

    validate_semester_value(semester)


def validate_student_dataframe(df: pd.DataFrame) -> None:
    """
    Validates the ``students`` DataFrame structure and types.
    Expected columns: ``id``, ``name``, ``email``, ``department``, ``semester``.
    Raises ValueError if any check fails.
    """
    required = {"id", "name", "email", "department", "semester"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Student DataFrame is missing columns: {missing}")

    if not pd.api.types.is_integer_dtype(df["id"]):
        raise ValueError("Column 'id' must be of integer type.")
    if (df["id"] <= 0).any():
        raise ValueError("Student IDs must be positive integers.")

    if df["name"].isnull().any() or (df["name"].astype(str).str.strip() == "").any():
        raise ValueError("Student names cannot be empty.")

    for idx, em in df["email"].items():
        if pd.notna(em) and str(em).strip() not in ["", "nan", "none"]:
            validate_email_value(em)

    for idx, sem in df["semester"].items():
        validate_semester_value(sem)


def validate_marks_dataframe(df: pd.DataFrame, allowed_subjects: Optional[Iterable[str]] = None) -> None:
    """
    Validates the ``marks`` DataFrame.
    Expected columns: ``id`` (student id), ``subject``, ``marks``.
    Raises ValueError if any check fails.
    """
    required = {"id", "subject", "marks"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Marks DataFrame is missing columns: {missing}")

    if not pd.api.types.is_integer_dtype(df["id"]):
        raise ValueError("Column 'id' in marks must be integer type.")
    if (df["id"] <= 0).any():
        raise ValueError("Student IDs in marks must be positive integers.")

    if df["subject"].isnull().any() or (df["subject"].astype(str).str.strip() == "").any():
        raise ValueError("Subject names cannot be empty.")

    if allowed_subjects is not None:
        invalid_subjects = set(df["subject"]) - set(allowed_subjects)
        if invalid_subjects:
            raise ValueError(f"Found unexpected subjects: {invalid_subjects}")

    for idx, m in df["marks"].items():
        validate_mark_value(m)


def audit_and_validate_dataset(df: pd.DataFrame) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    """
    Performs comprehensive pre-commit data validation on an imported DataFrame.
    Verifies:
    1. Duplicate normalized column headers.
    2. Student Names: non-empty, non-null, valid length >= 2 chars.
    3. Within-file duplicates: duplicate names or duplicate emails.
    4. Semester values: strictly between 1 and 12 (never silently defaulted).
    5. Email format: valid email regex pattern.
    6. Student_ID: valid positive integer without decimals if provided.
    7. Subject Marks: strictly numeric, non-null, strictly within [0, 100].

    Returns:
    - is_valid (bool)
    - errors (list of dicts with keys: Row, Column, Value, Description)
    - subject_cols (list of validated subject column names)
    """
    errors: List[Dict[str, Any]] = []

    # Check 1: Duplicate column names after normalization
    col_counts = pd.Series(df.columns).value_counts()
    dup_cols = col_counts[col_counts > 1].index.tolist()
    if dup_cols:
        errors.append({
            "Row": "Header",
            "Column": str(dup_cols),
            "Value": "Duplicate Column Names",
            "Description": f"Duplicate column headers detected after normalization: {', '.join(dup_cols)}. Remove or rename duplicate columns.",
        })
        return False, errors, []

    if "Name" not in df.columns:
        errors.append({
            "Row": "-",
            "Column": "Name",
            "Value": "Missing",
            "Description": "Dataset must contain a student 'Name' column.",
        })
        return False, errors, []

    meta_cols = ["Name", "Department", "Semester", "Email", "Student_ID"]
    subject_cols = [c for c in df.columns if c not in meta_cols]

    if not subject_cols:
        errors.append({
            "Row": "-",
            "Column": "Subjects",
            "Value": "None",
            "Description": "Dataset must contain at least one numerical subject column.",
        })
        return False, errors, []

    # Check 2: Student Names validation
    for idx, val in df["Name"].items():
        row_num = idx + 1
        s_val = str(val).strip() if pd.notna(val) else ""
        if not s_val or s_val.lower() in ["nan", "null", "none", ""]:
            errors.append({
                "Row": row_num,
                "Column": "Name",
                "Value": str(val),
                "Description": "Empty or invalid student name.",
            })
        elif len(s_val) < 2:
            errors.append({
                "Row": row_num,
                "Column": "Name",
                "Value": s_val,
                "Description": "Student name too short (minimum 2 characters required).",
            })

    # Check 3: Within-file duplicates
    name_counts = df["Name"].astype(str).str.strip().str.lower().value_counts()
    dup_names = name_counts[name_counts > 1].index.tolist()
    if dup_names:
        for idx, val in df["Name"].items():
            if str(val).strip().lower() in dup_names:
                errors.append({
                    "Row": idx + 1,
                    "Column": "Name",
                    "Value": str(val),
                    "Description": "Duplicate student name found within dataset.",
                })

    if "Email" in df.columns:
        valid_emails = df["Email"].dropna().astype(str).str.strip().str.lower()
        non_empty_emails = valid_emails[~valid_emails.isin(["", "nan", "none", "null"])]
        email_counts = non_empty_emails.value_counts()
        dup_emails = email_counts[email_counts > 1].index.tolist()
        if dup_emails:
            for idx, val in df["Email"].items():
                if pd.notna(val) and str(val).strip().lower() in dup_emails:
                    errors.append({
                        "Row": idx + 1,
                        "Column": "Email",
                        "Value": str(val),
                        "Description": "Duplicate email address found within dataset.",
                    })

    # Check 4: Semester strictly between 1 and 12
    if "Semester" in df.columns:
        for idx, val in df["Semester"].items():
            row_num = idx + 1
            try:
                validate_semester_value(val)
            except ValueError as ve:
                errors.append({
                    "Row": row_num,
                    "Column": "Semester",
                    "Value": str(val),
                    "Description": str(ve),
                })

    # Check 5: Email format regex
    if "Email" in df.columns:
        for idx, val in df["Email"].items():
            row_num = idx + 1
            if pd.notna(val) and str(val).strip() not in ["", "nan", "none", "null"]:
                try:
                    validate_email_value(val)
                except ValueError as ve:
                    errors.append({
                        "Row": row_num,
                        "Column": "Email",
                        "Value": str(val),
                        "Description": str(ve),
                    })

    # Check 6: Student_ID validation (strict positive integer, no decimals)
    if "Student_ID" in df.columns:
        for idx, val in df["Student_ID"].items():
            row_num = idx + 1
            if pd.notna(val) and str(val).strip() not in ["", "nan", "none", "null"]:
                try:
                    validate_student_id_value(val)
                except ValueError as ve:
                    errors.append({
                        "Row": row_num,
                        "Column": "Student_ID",
                        "Value": str(val),
                        "Description": str(ve),
                    })

    # Check 7: Marks validation for every subject column
    for sc in subject_cols:
        coerced = pd.to_numeric(df[sc], errors="coerce")
        null_count = coerced.isnull().sum()
        if null_count == len(df):
            errors.append({
                "Row": "All",
                "Column": sc,
                "Value": "Non-numeric",
                "Description": f"Subject column '{sc}' contains no valid numeric marks.",
            })
            continue

        for idx, mark in df[sc].items():
            row_num = idx + 1
            try:
                validate_mark_value(mark)
            except ValueError as ve:
                errors.append({
                    "Row": row_num,
                    "Column": sc,
                    "Value": str(mark),
                    "Description": str(ve),
                })

    is_valid = len(errors) == 0
    return is_valid, errors, subject_cols
