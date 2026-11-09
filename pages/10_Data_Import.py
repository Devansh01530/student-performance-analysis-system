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

from utils.validation import (
    CANONICAL_METADATA_MAP,
    normalize_headers,
    audit_and_validate_dataset,
    validate_student_id_value,
    validate_semester_value,
    validate_email_value,
    validate_mark_value,
)


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
                "Normalize column headers to canonical names (Department, Semester, Name, Email, Student_ID)",
                "Strip leading/trailing whitespace from text columns",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Drop rows containing empty student names",
                "Clamp marks strictly to [0, 100] range",
            ],
            default=[
                "Normalize column headers to canonical names (Department, Semester, Name, Email, Student_ID)",
                "Strip leading/trailing whitespace from text columns",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Drop rows containing empty student names",
                "Clamp marks strictly to [0, 100] range",
            ],
        )

        # Apply transformations
        clean_df = raw_df.copy()

        if "Normalize column headers to canonical names (Department, Semester, Name, Email, Student_ID)" in clean_opts:
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
                        All student names are valid, no duplicate records detected, semesters are strictly within [1, 12], and marks are strictly numerical within [0, 100].
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
                        The dataset contains empty names, duplicate students, invalid semesters, or invalid/missing marks. Review the audit table below.
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
            "Committing imported dataset executes an atomic SQLite transaction via the unified import pipeline."
        )

        commit_mode = st.radio(
            "Import Database Action",
            [
                "Append Records (Insert new students only - reject existing conflicts)",
                "Update Existing Records (Update existing matches and insert new students)",
                "Overwrite Database (Clear and replace all records)",
            ],
            help="Append mode protects existing records from accidental overwriting. Update mode refreshes existing student demographics and marks. Overwrite clears all tables with explicit confirmation.",
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
            try:
                is_overwrite = "Overwrite" in commit_mode
                is_update = "Update Existing Records" in commit_mode
                records_added = database.import_student_dataframe(clean_df, overwrite=is_overwrite, allow_updates=is_update)
                st.success(f"Database import complete. Successfully processed {records_added} student records and course marks.")
            except Exception as err:
                st.error(f"Database import failed: {err}")

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
                <br>• <b>Semester</b> (or Sem): Semester number strictly between 1 and 12
                <br>• <b>Email</b>: Institutional email address (format validated, duplicates flagged)
                <br>• <b>Student_ID</b> (or Roll_No, ID): Optional student identifier (matched if present)
                <br>• <b>Subject Columns</b>: Numerical score columns strictly within [0, 100]
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
