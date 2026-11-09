import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Academic Progress Tracking",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Academic Progress Tracking")
st.write(
    "Multi-examination monitoring: track longitudinal academic progression across Internal Assessments, Mid-Semester, and Final Examinations."
)

st.divider()

# Load Examinations and Progress Data
all_progress = database.get_all_exam_progress()
students = database.get_students()
exams = database.get_examinations()

if all_progress.empty or students.empty:
    st.info("No examination progress records available.")
else:
    # High-level Exam Averages
    st.subheader("Cohort Examination Benchmarks")

    exam_benchmarks = all_progress.groupby("exam_name")["marks"].agg(
        Average="mean",
        Highest="max",
        Lowest="min",
        Total_Evaluations="count",
    ).reset_index()
    exam_benchmarks["Average"] = exam_benchmarks["Average"].round(2)

    st.dataframe(exam_benchmarks, use_container_width=True, hide_index=True)

    # Examination comparison line chart across the cohort
    fig_cohort_exam = px.line(
        all_progress.groupby(["exam_name", "subject"])["marks"].mean().reset_index(),
        x="exam_name",
        y="marks",
        color="subject",
        markers=True,
        title="Curriculum Progression across Examination Milestones",
    )
    fig_cohort_exam.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        yaxis_range=[0, 105],
        xaxis_title="Examination Event",
        yaxis_title="Mean Score",
    )
    st.plotly_chart(fig_cohort_exam, use_container_width=True)

    st.divider()

    # Individual Student Progress Tracker
    st.subheader("Individual Student Longitudinal Tracking")

    sel_student_id = st.selectbox(
        "Select Student for Progress Audit",
        students["id"].tolist(),
        format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
    )

    s_progress = all_progress[all_progress["student_id"] == sel_student_id].copy()

    if s_progress.empty:
        st.info("No multi-examination records logged for this student.")
    else:
        student_name = s_progress.iloc[0]["name"]

        # Calculate student overall marks per exam
        exam_summary = s_progress.groupby(["exam_id", "exam_name"])["marks"].agg(
            Average="mean",
            Total="sum",
        ).reset_index().sort_values("exam_id")

        first_avg = exam_summary.iloc[0]["Average"]
        latest_avg = exam_summary.iloc[-1]["Average"]
        net_delta = round(latest_avg - first_avg, 2)
        net_pct = round(((latest_avg - first_avg) / first_avg) * 100, 2) if first_avg > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Initial Exam Average", f"{first_avg:.2f}")
        p2.metric("Latest Exam Average", f"{latest_avg:.2f}")
        p3.metric("Net Change", f"{net_delta:+.2f}")
        p4.metric("Growth Rate", f"{net_pct:+.2f}%")

        st.divider()

        # Subject-wise line chart for this student
        st.subheader(f"Subject Progression Trajectory for {student_name}")

        fig_ind_line = px.line(
            s_progress,
            x="exam_name",
            y="marks",
            color="subject",
            markers=True,
            text="marks",
            title=f"Course Trajectories across Examinations - {student_name}",
        )
        fig_ind_line.update_traces(textposition="top center")
        fig_ind_line.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            yaxis_range=[0, 110],
            xaxis_title="Examination Event",
            yaxis_title="Score",
        )
        st.plotly_chart(fig_ind_line, use_container_width=True)

        st.divider()

        # Subject-wise Improvement Table
        st.subheader("Subject-by-Subject Growth Audit")

        subj_pivot = s_progress.pivot_table(
            index="subject",
            columns="exam_name",
            values="marks",
            aggfunc="mean",
        ).reset_index()

        st.dataframe(subj_pivot, use_container_width=True, hide_index=True)

    st.divider()

    # Record New Examination Marks Form
    st.subheader("Log Examination Marks Event")

    with st.form("log_progress_exam_form"):
        col_pe1, col_pe2 = st.columns(2)
        with col_pe1:
            log_student_id = st.selectbox(
                "Student",
                students["id"].tolist(),
                format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
                key="pe_std",
            )
            log_exam_id = st.selectbox(
                "Examination Event",
                exams["id"].tolist(),
                format_func=lambda x: f"{exams.loc[exams['id'] == x, 'name'].iloc[0]}",
                key="pe_ex",
            )
        with col_pe2:
            log_subject = st.selectbox("Course Subject", ["Python", "C++", "Java", "Data Structures", "Database Management"])
            log_marks = st.number_input("Score Obtained (0-100)", min_value=0.0, max_value=100.0, value=82.0)

        submit_log = st.form_submit_button("Record Examination Result")
        if submit_log:
            database.save_marks(log_student_id, log_subject, log_marks, exam_id=log_exam_id)
            st.success(f"Examination mark of {log_marks} recorded for {log_subject}.")
            st.rerun()

