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

# Core Data
performance = get_student_performance()
subjects = get_subject_analysis()
metrics = get_dashboard_metrics()
students = database.get_students()

if performance.empty:
    st.info("No academic records available for dossier generation.")
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
        report_df = get_department_performance()
        report_title = "Department-Wise Comparative Performance Report"
        is_individual = False

    elif selected_report == "Semester Performance Report":
        report_df = get_semester_performance()
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
