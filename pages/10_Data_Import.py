import streamlit as st
import pandas as pd
import numpy as np
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
        # Pandas Operation: read_csv() or read_excel()
        if file_name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        st.success(f"File '{file_name}' loaded successfully. Total raw records: {len(raw_df)}")

        # Step 1: Raw Data Inspection
        st.subheader("Step 1: Raw Data Inspection (Pandas head & describe)")

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

        # Step 2: Data Quality & Anomaly Detection
        st.subheader("Step 2: Data Quality Audit")

        # Missing values (isnull)
        missing_count = int(raw_df.isnull().sum().sum())
        # Duplicate records (drop_duplicates)
        duplicate_count = int(raw_df.duplicated().sum())

        q1, q2, q3 = st.columns(3)
        q1.metric("Total Records", len(raw_df))
        q2.metric("Missing Value Cells", missing_count)
        q3.metric("Duplicate Rows", duplicate_count)

        st.divider()

        # Step 3: Interactive Cleaning Pipeline
        st.subheader("Step 3: Interactive Data Cleaning Operations")

        clean_opts = st.multiselect(
            "Select Cleaning Transformations to Apply",
            [
                "Strip leading/trailing whitespace from text columns",
                "Standardize column headers (remove special characters & spaces)",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Impute missing numeric values with column mean (Pandas fillna)",
                "Drop rows containing missing essential student names (Pandas dropna)",
                "Clamp marks strictly to [0, 100] range",
            ],
            default=[
                "Strip leading/trailing whitespace from text columns",
                "Standardize column headers (remove special characters & spaces)",
                "Drop duplicate rows (Pandas drop_duplicates)",
                "Impute missing numeric values with column mean (Pandas fillna)",
                "Drop rows containing missing essential student names (Pandas dropna)",
                "Clamp marks strictly to [0, 100] range",
            ],
        )

        # Apply transformations
        clean_df = raw_df.copy()

        if "Standardize column headers (remove special characters & spaces)" in clean_opts:
            clean_df.columns = clean_df.columns.astype(str).str.strip().str.replace("*", "", regex=False)

        if "Strip leading/trailing whitespace from text columns" in clean_opts:
            for col in clean_df.select_dtypes(include="object").columns:
                clean_df[col] = clean_df[col].astype(str).str.strip()

        if "Drop duplicate rows (Pandas drop_duplicates)" in clean_opts:
            clean_df = clean_df.drop_duplicates()

        # Find Name column
        name_col = None
        for c in clean_df.columns:
            if c.lower() == "name":
                name_col = c
                break

        if "Drop rows containing missing essential student names (Pandas dropna)" in clean_opts and name_col:
            clean_df = clean_df.dropna(subset=[name_col])
            clean_df = clean_df[clean_df[name_col] != "nan"]

        # Subject numeric columns
        meta_cols = [c for c in clean_df.columns if c.lower() in ["name", "email", "department", "semester", "id"]]
        numeric_subject_cols = [c for c in clean_df.columns if c not in meta_cols]

        for sc in numeric_subject_cols:
            clean_df[sc] = pd.to_numeric(clean_df[sc], errors="coerce")

        if "Impute missing numeric values with column mean (Pandas fillna)" in clean_opts and numeric_subject_cols:
            for sc in numeric_subject_cols:
                col_mean = clean_df[sc].mean()
                fill_val = round(col_mean, 2) if pd.notna(col_mean) else 50.0
                clean_df[sc] = clean_df[sc].fillna(fill_val)

        if "Clamp marks strictly to [0, 100] range" in clean_opts and numeric_subject_cols:
            for sc in numeric_subject_cols:
                clean_df[sc] = clean_df[sc].clip(lower=0.0, upper=100.0).round(2)

        st.subheader("Step 4: Cleaned Dataset Preview")
        st.dataframe(clean_df, use_container_width=True)

        st.divider()

        # Download Cleaned Dataset
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

        # Commit to Database
        st.subheader("Step 6: Commit to Database")

        st.warning(
            "Committing imported dataset will enroll these students and record their subject marks. "
            "Select an action mode below:"
        )

        commit_mode = st.radio(
            "Import Database Action",
            ["Append Records (keep existing students and attendance)", "Overwrite Database (replace all current records)"],
        )

        can_commit = True
        if "Overwrite" in commit_mode:
            confirm_overwrite = st.checkbox(
                "I explicitly confirm that overwriting will safely clear existing attendance, marks, and student records in foreign-key order."
            )
            can_commit = confirm_overwrite

        if st.button("Execute Database Import", disabled=not can_commit):
            if not name_col:
                st.error("Error: Dataset must contain a 'Name' column to identify students.")
            elif not numeric_subject_cols:
                st.error("Error: Dataset must contain at least one numerical subject column.")
            else:
                conn = database.get_connection()
                cursor = conn.cursor()

                try:
                    if "Overwrite" in commit_mode:
                        cursor.execute("DELETE FROM attendance")
                        cursor.execute("DELETE FROM marks")
                        cursor.execute("DELETE FROM students")

                    records_added = 0
                    for _, row in clean_df.iterrows():
                        s_name = str(row[name_col]).strip()
                        s_dept = str(row.get("Department", "BCA")).strip() if pd.notna(row.get("Department")) else "BCA"
                        s_sem = int(row.get("Semester", 3)) if pd.notna(row.get("Semester")) else 3
                        s_email = str(row.get("Email", "")).strip() if pd.notna(row.get("Email")) and str(row.get("Email", "")).strip() != "" else None

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

                        for sc in numeric_subject_cols:
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
                <br>• <b>Name</b>: Student full name (mandatory)
                <br>• <b>Department</b>: Academic department (e.g. BCA, B.Tech CSE, optional, default: BCA)
                <br>• <b>Semester</b>: Semester number (optional, default: 3)
                <br>• <b>Email</b>: Institutional email address (optional)
                <br>• <b>Subject Columns</b>: Numerical score columns (e.g. Python, C++, Java, Data Structures)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

