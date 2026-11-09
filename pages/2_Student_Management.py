import streamlit as st
import pandas as pd
import database
from utils import validation as val
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Student Management",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Student Management System")
st.write("Complete student lifecycle administration: enrollment, profile maintenance, course mark assignments, and record purge.")

st.divider()

# Navigation tabs for CRUD operations
tab_enroll, tab_directory, tab_profile, tab_marks, tab_remove = st.tabs([
    "Enroll Student",
    "Student Directory",
    "Update Profile",
    "Manage Marks",
    "Delete Record",
])

# 1. ENROLL STUDENT
with tab_enroll:
    st.subheader("Enroll New Student")

    with st.form("enroll_student_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Student Full Name")
            email = st.text_input("Institutional Email")
        with col2:
            dept_opts = ["BCA", "B.Tech CSE", "B.Sc IT", "MCA"]
            department = st.selectbox("Academic Department", dept_opts)
            semester = st.number_input("Semester (1-12)", min_value=1, max_value=12, value=3)

        st.markdown("#### Initial Examination Marks (Internal Assessment 1)")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            py_m = st.number_input("Python (0-100)", min_value=0.0, max_value=100.0, value=75.0)
        with m_col2:
            cpp_m = st.number_input("C++ (0-100)", min_value=0.0, max_value=100.0, value=75.0)
        with m_col3:
            java_m = st.number_input("Java (0-100)", min_value=0.0, max_value=100.0, value=75.0)

        submit_enroll = st.form_submit_button("Confirm Student Registration")

        if submit_enroll:
            try:
                val.validate_student_record(name, email, department, int(semester))
            except ValueError as err:
                st.error(str(err))
                st.stop()

            success = database.add_student(
                name.strip(),
                email.strip() or None,
                department.strip(),
                int(semester),
            )

            if success:
                latest_students = database.get_students()
                new_id = int(latest_students.iloc[-1]["id"])

                # Record marks for initial exam
                database.save_marks(new_id, "Python", py_m, exam_id=1)
                database.save_marks(new_id, "C++", cpp_m, exam_id=1)
                database.save_marks(new_id, "Java", java_m, exam_id=1)

                st.success(f"Student '{name.strip()}' registered with ID {new_id}.")
                st.rerun()
            else:
                st.error("Registration rejected: A student with this email address already exists.")

# 2. STUDENT DIRECTORY
with tab_directory:
    st.subheader("Student Directory & Search")

    all_students = database.get_students()

    if not all_students.empty:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            search_query = st.text_input("Search by Name or Student ID", placeholder="Filter by text...")
        with col_s2:
            dept_filters = ["All"] + sorted([d for d in all_students["department"].dropna().unique().tolist()])
            filter_dept = st.selectbox("Filter Department", dept_filters, key="dir_dept")
        with col_s3:
            sem_filters = ["All"] + sorted([int(s) for s in all_students["semester"].dropna().unique().tolist()])
            filter_sem = st.selectbox("Filter Semester", sem_filters, key="dir_sem")

        filtered_dir = all_students.copy()

        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_dir = filtered_dir[
                filtered_dir["name"].str.lower().str.contains(sq, na=False)
                | filtered_dir["id"].astype(str).str.contains(sq, na=False)
            ]

        if filter_dept != "All":
            filtered_dir = filtered_dir[filtered_dir["department"] == filter_dept]

        if filter_sem != "All":
            filtered_dir = filtered_dir[filtered_dir["semester"] == filter_sem]

        st.dataframe(
            filtered_dir[["id", "name", "email", "department", "semester", "created_at"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Displaying {len(filtered_dir)} of {len(all_students)} enrolled students.")
    else:
        st.info("The student database is currently empty.")

# 3. UPDATE PROFILE
with tab_profile:
    st.subheader("Update Student Profile")
    students = database.get_students()

    if students.empty:
        st.info("No student profiles available for updates.")
    else:
        selected_id = st.selectbox(
            "Select Student Record",
            students["id"].tolist(),
            format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
            key="profile_update_selector",
        )

        current = students[students["id"] == selected_id].iloc[0]

        with st.form("update_profile_form"):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                edit_name = st.text_input("Student Name", value=current["name"])
                edit_email = st.text_input("Institutional Email", value=current["email"] if pd.notna(current["email"]) else "")
            with col_p2:
                edit_dept = st.text_input("Department", value=current["department"])
                edit_sem = st.number_input("Semester", min_value=1, max_value=12, value=int(current["semester"]))

            submit_profile = st.form_submit_button("Save Profile Modifications")

            if submit_profile:
                try:
                    val.validate_student_record(edit_name, edit_email, edit_dept, int(edit_sem))
                except ValueError as err:
                    st.error(str(err))
                    st.stop()

                updated = database.update_student(
                    selected_id,
                    edit_name.strip(),
                    edit_email.strip() or None,
                    edit_dept.strip(),
                    int(edit_sem),
                )
                if updated:
                    st.success(f"Profile for ID {selected_id} updated successfully.")
                    st.rerun()
                else:
                    st.error("Update failed: Email address may conflict with an existing record.")

# 4. MANAGE MARKS
with tab_marks:
    st.subheader("Record and Update Examination Marks")
    students = database.get_students()
    exams = database.get_examinations()

    if students.empty:
        st.info("No enrolled students.")
    else:
        col_m_std, col_m_ex = st.columns(2)
        with col_m_std:
            target_student_id = st.selectbox(
                "Target Student",
                students["id"].tolist(),
                format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
                key="marks_student_selector",
            )
        with col_m_ex:
            target_exam_id = st.selectbox(
                "Examination Event",
                exams["id"].tolist(),
                format_func=lambda x: f"{exams.loc[exams['id'] == x, 'name'].iloc[0]}",
                key="marks_exam_selector",
            )

        existing_marks = database.get_marks(exam_id=target_exam_id)
        current_marks = existing_marks[existing_marks["id"] == target_student_id]

        if not current_marks.empty:
            st.write("Existing Marks for Selected Examination:")
            st.dataframe(current_marks[["subject", "marks", "exam_name"]], use_container_width=True, hide_index=True)

        with st.form("save_marks_form"):
            col_sb, col_sc = st.columns(2)
            with col_sb:
                subj_opts = ["Python", "C++", "Java", "Data Structures", "Database Management", "Custom"]
                sub_sel = st.selectbox("Subject", subj_opts)
                if sub_sel == "Custom":
                    custom_subj = st.text_input("Enter Custom Subject Name")
                else:
                    custom_subj = sub_sel
            with col_sc:
                mark_val = st.number_input("Assigned Score (0-100)", min_value=0.0, max_value=100.0, value=80.0)

            submit_mark = st.form_submit_button("Record Subject Mark")
            if submit_mark:
                final_subj = custom_subj.strip()
                if not final_subj:
                    st.error("Subject title cannot be empty.")
                else:
                    database.save_marks(target_student_id, final_subj, mark_val, exam_id=target_exam_id)
                    st.success(f"Mark of {mark_val} saved for {final_subj}.")
                    st.rerun()

# 5. DELETE RECORD
with tab_remove:
    st.subheader("Permanent Record Removal")
    students = database.get_students()

    if students.empty:
        st.info("No students enrolled.")
    else:
        del_id = st.selectbox(
            "Select Student to Delete",
            students["id"].tolist(),
            format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
            key="del_selector",
        )
        del_student = students[students["id"] == del_id].iloc[0]

        st.warning(
            f"You are requesting to permanently delete {del_student['name']} (ID: {del_id}). "
            "This will cascade and remove all associated examination marks and attendance records."
        )

        confirm_check = st.checkbox("I confirm that I want to remove this record permanently.")

        if st.button("Execute Permanent Record Deletion", disabled=not confirm_check):
            database.delete_student(del_id)
            st.success(f"Student record ID {del_id} deleted.")
            st.rerun()
