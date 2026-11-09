import streamlit as st
import pandas as pd
import plotly.express as px

import database
from utils.analysis import get_subject_analysis
from utils.style import apply_custom_css, add_sidebar_branding
import utils.charts_3d as charts3d

# Page configuration
st.set_page_config(
    page_title="Subject Diagnostics",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Subject-Wise Performance Analysis")
st.write(
    "Curriculum diagnostic engine: examine course difficulty, score spreads, pass/fail percentages, and 3D score landscapes."
)

st.divider()

# Examination Scope Filter
exams = database.get_examinations()
col_ex, _ = st.columns([1, 2])
with col_ex:
    exam_opts = [("All Examinations", None)] + [(r["name"], r["id"]) for _, r in exams.iterrows()]
    sel_exam_label = st.selectbox("Examination Scope", [opt[0] for opt in exam_opts])
    sel_exam_id = [opt[1] for opt in exam_opts if opt[0] == sel_exam_label][0]

# Subject Data
subject_data = get_subject_analysis(exam_id=sel_exam_id)
marks_data = database.get_marks(exam_id=sel_exam_id)

if subject_data.empty:
    st.info("No course performance data available for this examination scope.")
else:
    # Curriculum Overview
    st.subheader("Curriculum Health Overview")

    col1, col2, col3, col4 = st.columns(4)

    best_subject = subject_data.loc[subject_data["Average"].idxmax()]
    weak_subject = subject_data.loc[subject_data["Average"].idxmin()]

    col1.metric("Active Courses", len(subject_data))
    col2.metric("Highest Performing Subject", best_subject["subject"])
    col3.metric("Lowest Performing Subject", weak_subject["subject"])
    overall_mean = round(subject_data["Average"].mean(), 2)
    col4.metric("Curriculum Mean", f"{overall_mean:.2f}")

    st.divider()

    # Detailed Subject Metrics Table
    st.subheader("Course Performance Registry")
    st.dataframe(
        subject_data[[
            "subject", "Average", "Highest", "Lowest", "Pass_Percentage", "Fail_Percentage", "Students", "Difficulty"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # 3D Subject Landscape
    st.subheader("3D Subject Performance Landscape")
    st.write(
        "Interactive 3D elevation chart comparing Lowest, Average, and Highest metrics across all subjects."
    )
    fig_3d = charts3d.subject_landscape_3d(subject_data)
    st.plotly_chart(fig_3d, use_container_width=True)

    st.divider()

    # Range and Extremes Chart
    st.subheader("Score Spread & Extremes")

    range_data = subject_data.melt(
        id_vars=["subject"],
        value_vars=["Highest", "Lowest"],
        var_name="Metric",
        value_name="Marks",
    )

    fig_range = px.bar(
        range_data,
        x="subject",
        y="Marks",
        color="Metric",
        barmode="group",
        text="Marks",
        title="Highest vs Lowest Marks per Subject",
        color_discrete_map={"Highest": "#10b981", "Lowest": "#ef4444"},
    )
    fig_range.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig_range.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        xaxis_title="Subject",
        yaxis_title="Score",
        yaxis_range=[0, 110],
    )
    st.plotly_chart(fig_range, use_container_width=True)

    st.divider()

    # Pass vs Fail Percentages
    st.subheader("Course Pass vs Fail Distribution")

    pass_fail_data = subject_data.melt(
        id_vars=["subject"],
        value_vars=["Pass_Percentage", "Fail_Percentage"],
        var_name="Status",
        value_name="Percentage",
    )

    fig_pf = px.bar(
        pass_fail_data,
        x="subject",
        y="Percentage",
        color="Status",
        barmode="stack",
        text="Percentage",
        title="Pass and Fail Rates per Subject (%)",
        color_discrete_map={"Pass_Percentage": "#38bdf8", "Fail_Percentage": "#f43f5e"},
    )
    fig_pf.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
    fig_pf.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        yaxis_range=[0, 105],
    )
    st.plotly_chart(fig_pf, use_container_width=True)

    st.divider()

    # Statistical Dispersion: Box Plot & Marks Histogram
    st.subheader("Statistical Score Distribution (Box Plots & Density Histogram)")
    st.write(
        "Explore median scores, upper/lower quartiles (Q1, Q3), and dispersion spreads across all active courses."
    )

    box_col1, box_col2 = st.columns(2)

    with box_col1:
        fig_box = px.box(
            marks_data,
            x="subject",
            y="marks",
            color="subject",
            points="all",
            title="Course Score Distribution (Box Plot & Outliers)",
            color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f59e0b"],
        )
        fig_box.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            yaxis_title="Marks (0-100)",
            yaxis_range=[0, 105],
            showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with box_col2:
        fig_hist = px.histogram(
            marks_data,
            x="marks",
            color="subject",
            nbins=15,
            barmode="overlay",
            opacity=0.75,
            title="Curriculum Score Frequency Histogram",
            color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f59e0b"],
        )
        fig_hist.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            xaxis_title="Score Range",
            yaxis_title="Student Frequency",
            xaxis_range=[0, 105],
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # Course-Specific Student Drill Down
    st.subheader("Course-Specific Student Diagnostic")

    col_cs1, col_cs2 = st.columns([1, 1])
    with col_cs1:
        selected_subject = st.selectbox("Select Target Course", subject_data["subject"].tolist())
    with col_cs2:
        sort_order = st.selectbox("Sort Order", ["Descending (Highest First)", "Ascending (Lowest First)"])

    course_marks = marks_data[marks_data["subject"] == selected_subject].copy()
    ascending = True if "Ascending" in sort_order else False
    course_marks = course_marks.sort_values(by="marks", ascending=ascending)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Course Enrollment", len(course_marks))
    c2.metric("Mean Score", f"{course_marks['marks'].mean():.2f}")
    c3.metric("Top Score", f"{course_marks['marks'].max():.2f}")
    c4.metric("Lowest Score", f"{course_marks['marks'].min():.2f}")

    st.dataframe(
        course_marks[["name", "department", "semester", "marks"]],
        use_container_width=True,
        hide_index=True,
    )

    # Student comparison chart
    fig_course_bar = px.bar(
        course_marks,
        x="name",
        y="marks",
        color="marks",
        text="marks",
        title=f"Individual Student Performance in {selected_subject}",
        color_continuous_scale="Viridis",
    )
    fig_course_bar.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig_course_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        xaxis_title="Student",
        yaxis_title="Marks",
        yaxis_range=[0, 110],
    )
    st.plotly_chart(fig_course_bar, use_container_width=True)

    # Students Needing Improvement in this subject
    st.subheader(f"Students Requiring Support in {selected_subject}")
    subject_weak = course_marks[course_marks["marks"] < 50.0]

    if subject_weak.empty:
        st.info(f"All students have attained satisfactory marks (50 or above) in {selected_subject}.")
    else:
        st.dataframe(
            subject_weak[["name", "department", "semester", "marks"]],
            use_container_width=True,
            hide_index=True,
        )
