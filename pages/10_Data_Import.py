import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

import database
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Data Import and Cleaning",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Data Import, Cleaning, and Validation")
st.write(
    "Automated data pipeline: upload CSV or Excel student datasets, execute Pandas data-cleaning operations, validate schemas, and commit records to SQLite."
)

st.divider()

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


def normalize_headers(df):
    """
    Standardizes and normalizes dataframe column headers into canonical metadata names.
    Removes leading/trailing whitespace, punctuation asterisks/hashes,
    and maps case-insensitive variants (department, DEPARTMENT, Dept) to standard names.
    """
    renamed = {}
    for col in df.columns:
        c_str = str(col).strip().replace("*", "").replace("#", "")
        c_key = c_str.lower().replace(" ", "_").replace("-", "_")
        if c_key in CANONICAL_METADATA_MAP:
            renamed[col] = CANONICAL_METADATA_MAP[c_key]
        else:
            renamed[col] = c_str
    return df.rename(columns=renamed)


def audit_and_validate_dataset(df):
    """
    Performs comprehensive pre-commit data validation.
    Verifies:
    1. Student Names: non-empty, non-null, valid length.
    2. Duplicates: within-dataset duplicate student names or emails.
    3. Subject Marks: strictly numeric, non-null, strictly within [0, 100].
    Returns:
    - is_valid (bool)
    - errors (list of dicts with Row, Column, Value, Description)
    - subject_cols (list of validated subject columns)
    """
    errors = []
    
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

    # Check 1: Student Names validation
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

    # Check 2: Within-file duplicates
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
        valid_emails = df["Email"].dropna().astype(str).str.strip()
        email_counts = valid_emails[valid_emails != ""].str.lower().value_counts()
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

    # Check 3: Marks validation for every subject column
    for sc in subject_cols:
        # Check if entire column is non-numeric
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
            if pd.isna(mark):
                errors.append({
                    "Row": row_num,
                    "Column": sc,
                    "Value": "Missing (NaN)",
                    "Description": f"Missing mark in subject '{sc}'. Empty marks are not permitted.",
                })
            else:
                try:
                    f_val = float(mark)
                    if np.isnan(f_val):
                        errors.append({
                            "Row": row_num,
                            "Column": sc,
                            "Value": "NaN",
                            "Description": f"Invalid NaN mark in subject '{sc}'.",
                        })
                    elif f_val < 0.0 or f_val > 100.0:
                        errors.append({
                            "Row": row_num,
                            "Column": sc,
                            "Value": str(mark),
                            "Description": f"Mark {f_val} is outside acceptable [0, 100] range.",
                        })
                except (ValueError, TypeError):
                    errors.append({
                        "Row": row_num,
                        "Column": sc,
                        "Value": str(mark),
                        "Description": f"Non-numeric value in subject '{sc}'.",
                    })

    is_valid = len(errors) == 0
    return is_valid, errors, subject_cols


# Upload Control
st.subheader("Upload Academic Dataset")
uploaded_file = st.file_uploader(
    "Select Dataset File (CSV or Excel XLSX)",
    type=["csv", "xlsx", "xls"],
    help="Dataset must contain a Name column along with subject score columns.",
)

if uploaded_file is not None:
    file_name = uploaded_file.name

    try:
        # Read file
        if file_name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        st.success(f"File '{file_name}' loaded successfully. Total raw records: {len(raw_df)}")

        # Step 1: Raw Data Inspection
        st.subheader("Step 1: Raw Data Inspection")

        tab_head, tab_describe, tab_info = st.tabs(["Data Preview (head)", "Statistical Summary (describe)", "Schema & Types"])

        with tab_head:
            st.dataframe(raw_df.head(10), use_container_width=True)

        with tab_describe:
            st.dataframe(raw_df.describe(), use_container_width=True)

        with tab_info:
            info_df = pd.DataFrame({
                "Column": raw_df.columns,
                "Non-Null Count": raw_df.notnull().sum().values,
                "Null Count": raw_df.isnull().sum().values,
                "Dtype": [str(t) for t in raw_df.dtypes.values],
            })
            st.dataframe(info_df, use_container_width=True, hide_index=True)

        st.divider()

        # Step 2: Interactive Cleaning Pipeline
        st.subheader("Step 2: Interactive Data Cleaning & Standardization")

        clean_opts = st.multiselect(
            "Select Cleaning Transformations to Apply",
            [
                "Normalize column headers to canonical names (Department, Semester, Name, Email)",
                "Strip leading/trailing whitespace from text columns",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Drop rows containing empty student names",
                "Clamp marks strictly to [0, 100] range",
            ],
            default=[
                "Normalize column headers to canonical names (Department, Semester, Name, Email)",
                "Strip leading/trailing whitespace from text columns",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Drop rows containing empty student names",
                "Clamp marks strictly to [0, 100] range",
            ],
        )

        # Apply transformations
        clean_df = raw_df.copy()

        if "Normalize column headers to canonical names (Department, Semester, Name, Email)" in clean_opts:
            clean_df = normalize_headers(clean_df)

        if "Strip leading/trailing whitespace from text columns" in clean_opts:
            for col in clean_df.select_dtypes(include="object").columns:
                clean_df[col] = clean_df[col].astype(str).str.strip()

        if "Drop duplicate rows (Pandas drop_duplicates)" in clean_opts:
            clean_df = clean_df.drop_duplicates()

        # Resolve Name column
        name_col = "Name" if "Name" in clean_df.columns else None
        if not name_col:
            for c in clean_df.columns:
                if str(c).strip().lower() in ["name", "student_name"]:
                    name_col = c
                    clean_df = clean_df.rename(columns={c: "Name"})
                    name_col = "Name"
                    break

        if "Drop rows containing empty student names" in clean_opts and name_col:
            clean_df = clean_df.dropna(subset=[name_col])
            clean_df = clean_df[~clean_df[name_col].astype(str).str.lower().isin(["nan", "null", "none", ""])]

        # Identify subject columns
        meta_cols = ["Name", "Department", "Semester", "Email", "Student_ID"]
        subject_cols = [c for c in clean_df.columns if c not in meta_cols]

        if "Clamp marks strictly to [0, 100] range" in clean_opts and subject_cols:
            for sc in subject_cols:
                # Convert numeric, leaving genuine unparseable values as NaN for strict rejection
                clean_df[sc] = pd.to_numeric(clean_df[sc], errors="coerce")
                clean_df[sc] = clean_df[sc].clip(lower=0.0, upper=100.0).round(2)

        st.subheader("Step 3: Cleaned Dataset Preview")
        st.dataframe(clean_df, use_container_width=True)

        st.divider()

        # Step 4: Pre-Commit Validation & Audit Gate
        st.subheader("Step 4: Pre-Commit Integrity Validation")

        is_valid, validation_errors, validated_subjects = audit_and_validate_dataset(clean_df)

        if is_valid:
            st.markdown(
                """
                <div class="card-3d" style="border-left: 4px solid #34d399; margin-bottom: 16px;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #34d399; font-weight: 700;">
                        Integrity Audit Passed
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: #ffffff; margin-top: 4px;">
                        Dataset Ready for Database Insertion
                    </div>
                    <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                        All student names are valid, no duplicate records detected, and all subject marks are strictly numerical within [0, 100].
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="card-3d" style="border-left: 4px solid #f87171; margin-bottom: 16px;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #f87171; font-weight: 700;">
                        Integrity Audit Warning: {len(validation_errors)} Issues Detected
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: #ffffff; margin-top: 4px;">
                        Database Commit Blocked Until Resolved
                    </div>
                    <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                        The dataset contains empty names, duplicate students, or invalid/missing marks. Review the audit table below.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            err_df = pd.DataFrame(validation_errors)
            st.dataframe(err_df, use_container_width=True, hide_index=True)

            if st.button("Auto-Filter: Exclude Invalid Rows"):
                invalid_row_indices = [
                    int(e["Row"]) - 1 for e in validation_errors if isinstance(e["Row"], int)
                ]
                clean_df = clean_df.drop(index=invalid_row_indices).reset_index(drop=True)
                st.success("Invalid rows successfully excluded. Re-evaluating dataset...")
                st.rerun()

        st.divider()

        # Step 5: Export Cleaned Dataset
        st.subheader("Step 5: Export Cleaned Dataset")
        col_cd1, col_cd2 = st.columns(2)

        with col_cd1:
            csv_clean = clean_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Cleaned CSV", csv_clean, "cleaned_student_dataset.csv", "text/csv")

        with col_cd2:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                clean_df.to_excel(writer, sheet_name="Cleaned Data", index=False)
            st.download_button(
                "Download Cleaned Excel",
                excel_buffer.getvalue(),
                "cleaned_student_dataset.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.divider()

        # Step 6: Commit to Database
        st.subheader("Step 6: Commit to Database")

        st.write(
            "Committing imported dataset enrolls students and records their course marks in SQLite."
        )

        commit_mode = st.radio(
            "Import Database Action",
            ["Append Records (keep existing students and attendance)", "Overwrite Database (replace all current records)"],
        )

        can_commit = is_valid
        if "Overwrite" in commit_mode:
            confirm_overwrite = st.checkbox(
                "I explicitly confirm that overwriting will safely clear existing attendance, marks, and student records in foreign-key order."
            )
            can_commit = is_valid and confirm_overwrite

        if not is_valid:
            st.caption("Database import button is disabled until all validation errors are resolved or filtered out.")

        if st.button("Execute Database Import", disabled=not can_commit):
            conn = database.get_connection()
            cursor = conn.cursor()

            try:
                if "Overwrite" in commit_mode:
                    cursor.execute("DELETE FROM attendance")
                    cursor.execute("DELETE FROM marks")
                    cursor.execute("DELETE FROM students")

                records_added = 0
                for _, row in clean_df.iterrows():
                    s_name = str(row["Name"]).strip()
                    s_dept = str(row.get("Department", "BCA")).strip() if pd.notna(row.get("Department")) and str(row.get("Department", "")).strip() != "" else "BCA"
                    
                    try:
                        s_sem = int(row.get("Semester", 3)) if pd.notna(row.get("Semester")) else 3
                    except (ValueError, TypeError):
                        s_sem = 3

                    raw_email = row.get("Email")
                    s_email = str(raw_email).strip() if pd.notna(raw_email) and str(raw_email).strip() not in ["", "nan", "none"] else None

                    student_id = None
                    if "Append" in commit_mode:
                        if s_email:
                            cursor.execute("SELECT id FROM students WHERE email = ?", (s_email,))
                            match = cursor.fetchone()
                            if match:
                                student_id = match[0]
                        if student_id is None:
                            cursor.execute("SELECT id FROM students WHERE name = ? AND department = ?", (s_name, s_dept))
                            match = cursor.fetchone()
                            if match:
                                student_id = match[0]

                    if student_id is None:
                        cursor.execute("""
                            INSERT INTO students (name, email, department, semester)
                            VALUES (?, ?, ?, ?)
                        """, (s_name, s_email, s_dept, s_sem))
                        student_id = cursor.lastrowid

                    for sc in validated_subjects:
                        mark_val = float(row[sc])
                        cursor.execute("""
                            SELECT id FROM marks
                            WHERE student_id = ? AND subject = ? AND exam_id = 1
                        """, (student_id, sc))
                        m_match = cursor.fetchone()
                        if m_match:
                            cursor.execute("UPDATE marks SET marks = ? WHERE id = ?", (mark_val, m_match[0]))
                        else:
                            cursor.execute("""
                                INSERT INTO marks (student_id, subject, marks, exam_id)
                                VALUES (?, ?, ?, 1)
                            """, (student_id, sc, mark_val))

                    records_added += 1

                conn.commit()
                st.success(f"Database import complete. Successfully processed {records_added} student records and course marks.")
            except Exception as err:
                conn.rollback()
                st.error(f"Database import failed: {err}")
            finally:
                conn.close()

    except Exception as e:
        st.error(f"Failed to process file: {e}")
else:
    # Guidelines when no file is uploaded
    st.markdown(
        """
        <div class="card-3d">
            <div style="font-size: 1.1rem; font-weight: 600; color: #ffffff; margin-bottom: 8px;">
                Dataset Format Requirements
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.6;">
                Uploaded files should include the following schema:
                <br>• <b>Name</b> (or Student_Name, Full_Name): Student full name (mandatory)
                <br>• <b>Department</b> (or Dept, Branch): Academic department (case-insensitive, default: BCA)
                <br>• <b>Semester</b> (or Sem): Semester number (optional, default: 3)
                <br>• <b>Email</b>: Institutional email address (optional, duplicates flagged)
                <br>• <b>Subject Columns</b>: Numerical score columns (e.g. Python, C++, Java, Data Structures) strictly within [0, 100]
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
