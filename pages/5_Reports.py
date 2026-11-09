import streamlit as st
import pandas as pd
from io import BytesIO

import database
from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_department_performance,
    get_semester_performance,
    get_dashboard_metrics,
)
from utils.predict import train_and_evaluate_models
from utils.recommendations import get_cohort_risk_overview
from utils.report_generator import (
    generate_pdf_report,
    generate_student_report_card_pdf,
    generate_excel_dossier,
)
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Institutional Reports",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Reports and Data Export Center")
st.write(
    "Generate, inspect, and download official institutional academic reports in PDF, CSV, and multi-sheet Excel formats."
)

st.divider()

# Examination Scope Filter
exams = database.get_examinations()
exam_scope_options = []
if not exams.empty:
    exams_sorted = exams.copy()
    exams_sorted["parsed_date"] = pd.to_datetime(exams_sorted["exam_date"], errors="coerce")
    exams_sorted = exams_sorted.sort_values(by=["parsed_date", "id"], na_position="first")
    latest_exam = exams_sorted.iloc[-1]
    
    exam_scope_options.append((f"Latest Examination: {latest_exam['name']}", int(latest_exam["id"]), False))
    for _, r in exams.iterrows():
        exam_scope_options.append((f"Single Examination: {r['name']}", int(r["id"]), False))
    exam_scope_options.append(("Cumulative Across All Examinations (Intentionally Aggregated)", None, True))

col_rep_scope, _ = st.columns([1, 2])
with col_rep_scope:
    sel_rep_label = st.selectbox(
        "Report Examination Scope",
        options=[opt[0] for opt in exam_scope_options] if exam_scope_options else ["Default Scope"],
        index=0,
    )

sel_exam_id = None
sel_allow_all = False
for label, e_id, allow_all in exam_scope_options:
    if label == sel_rep_label:
        sel_exam_id = e_id
        sel_allow_all = allow_all
        break

# Core Data for selected examination scope
performance = get_student_performance(exam_id=sel_exam_id, allow_all=sel_allow_all)
subjects = get_subject_analysis(exam_id=sel_exam_id, allow_all=sel_allow_all)
metrics = get_dashboard_metrics(exam_id=sel_exam_id, allow_all=sel_allow_all)
students = database.get_students()

if performance.empty:
    st.info("No academic records available for dossier generation in this examination scope.")
else:
    active_scope_name = performance.iloc[0].get("Exam_Scope", "Selected Examination Scope")
    st.caption(f"Active Report Evaluation Scope: **{active_scope_name}**")
else:
    # Summary Cards
    st.subheader("Executive Cohort Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Enrolled Cohort", metrics["total_students"])
    c2.metric("Institution Mean", f"{metrics['class_average']:.2f}")
    c3.metric("Passing Rate", f"{metrics['pass_percentage']}%")
    c4.metric("At-Risk Count", metrics["failed_students"])

    st.divider()

    # Report Selection
    st.subheader("Configure Report Output")

    report_types = [
        "Complete Student Performance Report",
        "Individual Student Report Card",
        "Subject Performance Report",
        "Department Performance Report",
        "Semester Performance Report",
        "Attendance Registry Report",
        "Academic Progress Report",
        "Predictive Analytics Report",
    ]

    selected_report = st.selectbox("Select Report Type", report_types)

    # Prepare DataFrame and titles based on selection
    if selected_report == "Complete Student Performance Report":
        report_df = performance.copy()
        report_title = "Comprehensive Cohort Academic Performance Report"
        is_individual = False

    elif selected_report == "Individual Student Report Card":
        is_individual = True
        sel_student_id = st.selectbox(
            "Select Student Profile",
            students["id"].tolist(),
            format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
        )
        report_df = performance[performance["id"] == sel_student_id].copy()
        s_name = report_df.iloc[0]["name"] if not report_df.empty else f"Student_{sel_student_id}"
        report_title = f"Official Academic Report Card - {s_name}"

    elif selected_report == "Subject Performance Report":
        report_df = subjects.copy()
        report_title = "Curriculum Subject Diagnostics Report"
        is_individual = False

    elif selected_report == "Department Performance Report":
        report_df = get_department_performance(exam_id=sel_exam_id, allow_all=sel_allow_all)
        report_title = "Department-Wise Comparative Performance Report"
        is_individual = False

    elif selected_report == "Semester Performance Report":
        report_df = get_semester_performance(exam_id=sel_exam_id, allow_all=sel_allow_all)
        report_title = "Semester-Wise Academic Progression Report"
        is_individual = False

    elif selected_report == "Attendance Registry Report":
        report_df = database.get_attendance_summary()
        report_title = "Institutional Attendance Registry Report"
        is_individual = False

    elif selected_report == "Academic Progress Report":
        report_df = database.get_all_exam_progress()
        report_title = "Multi-Examination Academic Progress Tracking Report"
        is_individual = False

    else:  # Predictive Analytics Report
        ml_results = train_and_evaluate_models()
        if ml_results.get("status") == "success":
            report_df = ml_results["cohort_predictions"].copy()
        else:
            report_df = performance.copy()
        report_title = "Machine Learning Predictive Performance Report"
        is_individual = False

    # Preview Table
    st.subheader("Report Table Preview")
    st.dataframe(report_df, use_container_width=True, hide_index=True)

    st.divider()

    # Download Controls
    st.subheader("Export Formats")

    col_pdf, col_csv, col_xlsx = st.columns(3)

    with col_pdf:
        if is_individual:
            pdf_data = generate_student_report_card_pdf(sel_student_id)
            pdf_filename = f"report_card_student_{sel_student_id}.pdf"
        else:
            pdf_data = generate_pdf_report(report_df, report_title)
            pdf_filename = f"{selected_report.lower().replace(' ', '_')}.pdf"

        st.download_button(
            label="Download Formatted PDF",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf",
        )

    with col_csv:
        csv_data = report_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Standard CSV",
            data=csv_data,
            file_name=f"{selected_report.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

    with col_xlsx:
        excel_bytes = generate_excel_dossier()
        st.download_button(
            label="Download Multi-Sheet Excel Dossier",
            data=excel_bytes,
            file_name="academic_intelligence_dossier.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
