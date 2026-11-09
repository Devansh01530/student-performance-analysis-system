import streamlit as st
import pandas as pd
import plotly.express as px

from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_dashboard_metrics,
    get_department_performance,
    get_semester_performance,
    get_attendance_analytics,
)
from utils.charts import (
    student_performance_chart,
    subject_average_chart,
    grade_distribution_chart,
    pass_fail_chart,
)
import utils.charts_3d as charts3d
from utils.style import apply_custom_css, add_sidebar_branding

# Page configuration
st.set_page_config(
    page_title="Executive Dashboard",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

import database

# Title
st.title("Academic Performance Dashboard")
st.write(
    "Institutional intelligence overview: academic trends, multi-department diagnostics, and spatial projections."
)

st.divider()

# Examination Scope Selection
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

col_es, _ = st.columns([1, 2])
with col_es:
    sel_label = st.selectbox(
        "Examination Evaluation Scope",
        options=[opt[0] for opt in exam_scope_options] if exam_scope_options else ["Default Scope"],
    )

sel_exam_id = None
sel_allow_all = False
for label, e_id, allow_all in exam_scope_options:
    if label == sel_label:
        sel_exam_id = e_id
        sel_allow_all = allow_all
        break

# Load Core Data for selected examination scope
performance = get_student_performance(exam_id=sel_exam_id, allow_all=sel_allow_all)
subjects = get_subject_analysis(exam_id=sel_exam_id, allow_all=sel_allow_all)
metrics = get_dashboard_metrics(exam_id=sel_exam_id, allow_all=sel_allow_all)
att_stats = get_attendance_analytics()

if performance.empty:
    st.info("No student records available in the database for the selected examination scope. Use Student Management or Data Import to add records.")
else:
    # Active Scope Indicator
    active_scope_name = performance.iloc[0].get("Exam_Scope", "Selected Examination Scope")
    st.caption(f"Active Evaluation Scope: **{active_scope_name}**")

    # Interactive Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        dept_options = ["All Departments"] + sorted([d for d in performance["department"].dropna().unique().tolist()])
        selected_dept = st.selectbox("Department Filter", dept_options)
    with col_f2:
        sem_options = ["All Semesters"] + sorted([int(s) for s in performance["semester"].dropna().unique().tolist()])
        selected_sem = st.selectbox("Semester Filter", sem_options)

    # Filtered dataset
    filtered_perf = performance.copy()
    if selected_dept != "All Departments":
        filtered_perf = filtered_perf[filtered_perf["department"] == selected_dept]
    if selected_sem != "All Semesters":
        filtered_perf = filtered_perf[filtered_perf["semester"] == selected_sem]

    # Recalculate metrics for active filters
    total_active = len(filtered_perf)
    avg_active = float(filtered_perf["Average"].mean()) if total_active > 0 else 0.0
    passed_active = (filtered_perf["Status"] == "Pass").sum() if total_active > 0 else 0
    pass_pct_active = round((passed_active / total_active) * 100, 2) if total_active > 0 else 0.0
    fail_pct_active = round(100.0 - pass_pct_active, 2) if total_active > 0 else 0.0
    high_avg_active = float(filtered_perf["Average"].max()) if total_active > 0 else 0.0
    need_support_active = (filtered_perf["Status"] == "Fail").sum() if total_active > 0 else 0

    st.subheader("Key Performance Indicators")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Enrolled Cohort", total_active)
    m_col2.metric("Cohort Mean", f"{avg_active:.2f}")
    m_col3.metric("Pass Rate", f"{pass_pct_active}%")
    m_col4.metric("Fail Rate", f"{fail_pct_active}%")

    m_col5, m_col6, m_col7, m_col8 = st.columns(4)
    m_col5.metric("Peak Average", f"{high_avg_active:.2f}")
    m_col6.metric("Requiring Support", need_support_active)
    m_col7.metric("Average Attendance", att_stats["overall_display"])
    m_col8.metric("Evaluated Courses", metrics["total_subjects"])

    # High-level Strongest / Weakest Course Callout
    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        st.markdown(
            f"""
            <div class="card-3d">
                <div style="font-size: 0.8rem; text-transform: uppercase; color: #38bdf8; font-weight: 700;">Curriculum Highlight</div>
                <div style="font-size: 1.3rem; font-weight: 600; color: #ffffff; margin-top: 4px;">Strongest Subject: {metrics['strongest_subject']}</div>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Demonstrates highest overall student mastery and mean score.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_sub2:
        st.markdown(
            f"""
            <div class="card-3d">
                <div style="font-size: 0.8rem; text-transform: uppercase; color: #f43f5e; font-weight: 700;">Curriculum Alert</div>
                <div style="font-size: 1.3rem; font-weight: 600; color: #ffffff; margin-top: 4px;">Weakest Subject: {metrics['weakest_subject']}</div>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Identified lowest score average. Targeted faculty intervention recommended.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # 3D Spatial Performance Projection
    st.subheader("3D Spatial Performance Projection")
    st.write(
        "Interactive 3D view mapping Semester (X) by Average Marks (Y) by Total Points (Z). "
        "Top-ranked students feature prominent markers in 3D coordinate space."
    )
    fig_3d = charts3d.student_performance_3d(filtered_perf)
    st.plotly_chart(fig_3d, use_container_width=True)

    st.divider()

    # 2D Performance Charts
    st.subheader("Comparative Academic Breakdown")

    tab_students, tab_subjects = st.tabs(["Student Comparisons", "Subject Performance Radar"])

    with tab_students:
        fig1 = student_performance_chart(filtered_perf)
        st.plotly_chart(fig1, use_container_width=True)

    with tab_subjects:
        fig2 = subject_average_chart(subjects)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Grade & Pass/Fail Distributions
    st.subheader("Cohort Distribution Profiles")
    dist1, dist2 = st.columns(2)

    with dist1:
        fig3 = grade_distribution_chart(filtered_perf)
        st.plotly_chart(fig3, use_container_width=True)

    with dist2:
        fig4 = pass_fail_chart(filtered_perf)
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # Department & Semester Comparisons
    st.subheader("Macro Institutional Comparisons")
    macro1, macro2 = st.columns(2)

    with macro1:
        dept_df = get_department_performance()
        if not dept_df.empty:
            fig_dept = px.bar(
                dept_df,
                x="department",
                y="Average",
                color="department",
                text="Average",
                title="Department-Wise Mean Performance",
                color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f59e0b"],
            )
            fig_dept.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig_dept.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                yaxis_range=[0, 105],
                showlegend=False,
            )
            st.plotly_chart(fig_dept, use_container_width=True)

    with macro2:
        sem_df = get_semester_performance()
        if not sem_df.empty:
            fig_sem = px.bar(
                sem_df,
                x="semester",
                y="Average",
                color="semester",
                text="Average",
                title="Semester-Wise Progression Mean",
                color_continuous_scale="Viridis",
            )
            fig_sem.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig_sem.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                yaxis_range=[0, 105],
            )
            st.plotly_chart(fig_sem, use_container_width=True)

    st.divider()

    # Top Performers vs Students Needing Support
    list_col1, list_col2 = st.columns(2)

    with list_col1:
        st.subheader("Top Five Performing Students")
        top_5 = filtered_perf.head(5)
        st.dataframe(
            top_5[["Rank", "name", "department", "semester", "Average", "Grade", "Status"]],
            use_container_width=True,
            hide_index=True,
        )

    with list_col2:
        st.subheader("Students Requiring Academic Support")
        weak_list = filtered_perf[
            (filtered_perf["Average"] < 40.0) | (filtered_perf["Status"] == "Fail")
        ]
        if weak_list.empty:
            st.info("All registered students in this selection meet minimum passing criteria.")
        else:
            st.dataframe(
                weak_list[["Rank", "name", "department", "semester", "Average", "Grade", "Status"]],
                use_container_width=True,
                hide_index=True,
            )
