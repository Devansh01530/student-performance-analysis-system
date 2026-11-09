import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

from utils.analysis import get_student_performance, get_subject_correlation
import database
from utils.style import apply_custom_css, add_sidebar_branding
import utils.charts_3d as charts3d

# Page configuration
st.set_page_config(
    page_title="Performance Analysis",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Academic Performance Analysis")
st.write(
    "Deep academic analytics: cohort ranking, grade calculations, multi-filter segmentation, and correlation matrices."
)

st.divider()

# Examination Selector
exams = database.get_examinations()
exam_options = []
if not exams.empty:
    exams_sorted = exams.copy()
    exams_sorted["parsed_date"] = pd.to_datetime(exams_sorted["exam_date"], errors="coerce")
    exams_sorted = exams_sorted.sort_values(by=["parsed_date", "id"], na_position="first")
    latest_exam = exams_sorted.iloc[-1]
    
    exam_options.append((f"Latest Examination: {latest_exam['name']}", int(latest_exam["id"]), False))
    for _, r in exams.iterrows():
        exam_options.append((f"Single Examination: {r['name']}", int(r["id"]), False))
    exam_options.append(("Cumulative Across All Examinations (Intentionally Aggregated)", None, True))

col_ex, _ = st.columns([1, 2])
with col_ex:
    selected_exam_label = st.selectbox(
        "Examination Evaluation Scope",
        options=[opt[0] for opt in exam_options] if exam_options else ["Default Scope"],
        index=0,
    )

selected_exam_id = None
selected_allow_all = False
for label, e_id, allow_all in exam_options:
    if label == selected_exam_label:
        selected_exam_id = e_id
        selected_allow_all = allow_all
        break

df = get_student_performance(exam_id=selected_exam_id, allow_all=selected_allow_all)

if df.empty:
    st.info("No student performance records available for this selection.")
else:
    active_scope_name = df.iloc[0].get("Exam_Scope", "Selected Examination Scope")
    st.caption(f"Active Evaluation Scope: **{active_scope_name}**")

    # Centralized Filter Matrix
    st.subheader("Filter & Segmentation Parameters")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search = st.text_input("Search Student Name", placeholder="Enter name...")
    with col2:
        grade_opts = ["All"] + sorted([g for g in df["Grade"].dropna().unique().tolist()])
        selected_grade = st.selectbox("Grade Category", grade_opts)
    with col3:
        status_opts = ["All", "Pass", "Fail"]
        selected_status = st.selectbox("Academic Standing", status_opts)
    with col4:
        dept_opts = ["All"] + sorted([d for d in df["department"].dropna().unique().tolist()])
        selected_dept = st.selectbox("Department", dept_opts)

    col5, col6 = st.columns(2)
    with col5:
        sem_opts = ["All"] + sorted([int(s) for s in df["semester"].dropna().unique().tolist()])
        selected_sem = st.selectbox("Semester", sem_opts)
    with col6:
        min_avg, max_avg = st.slider("Average Score Range", 0.0, 100.0, (0.0, 100.0), step=1.0)

    # Filter execution
    filtered_df = df.copy()

    if search.strip():
        filtered_df = filtered_df[filtered_df["name"].str.contains(search.strip(), case=False, na=False)]
    if selected_grade != "All":
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["Status"] == selected_status]
    if selected_dept != "All":
        filtered_df = filtered_df[filtered_df["department"] == selected_dept]
    if selected_sem != "All":
        filtered_df = filtered_df[filtered_df["semester"] == selected_sem]

    filtered_df = filtered_df[(filtered_df["Average"] >= min_avg) & (filtered_df["Average"] <= max_avg)]

    st.divider()

    # Performance Summary Cards
    st.subheader("Cohort Analysis Overview")

    if filtered_df.empty:
        st.info("No students match the specified filtering parameters.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Selected Students", len(filtered_df))
        k1_avg = filtered_df["Average"].mean()
        k2.metric("Mean Average Score", f"{k1_avg:.2f}")
        k3.metric("Highest Average", f"{filtered_df['Average'].max():.2f}")
        k4.metric("Lowest Average", f"{filtered_df['Average'].min():.2f}")

        st.divider()

        # Grade Registry Table
        st.subheader("Official Performance Registry")
        display_columns = [
            c for c in ["Rank", "name", "department", "semester", "Average", "Total", "Grade", "Status"]
            if c in filtered_df.columns
        ]
        st.dataframe(filtered_df[display_columns], use_container_width=True, hide_index=True)

        # Export Controls
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export Registry (CSV)", csv_bytes, "cohort_registry.csv", "text/csv")
        with col_down2:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                filtered_df.to_excel(writer, sheet_name="Filtered Performance", index=False)
            st.download_button("Export Registry (Excel)", excel_buffer.getvalue(), "cohort_registry.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.divider()

        # Visual Comparison Bar
        st.subheader("Student Score Comparison")
        fig_bar = px.bar(
            filtered_df,
            x="name",
            y="Average",
            color="Grade",
            text="Average",
            title="Individual Cohort Standings",
            color_discrete_map={
                "A+": "#38bdf8",
                "A": "#60a5fa",
                "B": "#818cf8",
                "C": "#a78bfa",
                "D": "#f59e0b",
                "F": "#ef4444",
            },
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            xaxis_title="Student Name",
            yaxis_title="Average Marks",
            yaxis_range=[0, 105],
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Subject Correlation Matrix (Pandas Correlation)
    st.subheader("Curriculum Correlation Analysis")
    st.write(
        "Pearson correlation matrix computed via Pandas. Identifies statistical co-dependency and shared performance trends between subjects."
    )

    corr_df = get_subject_correlation()
    if not corr_df.empty:
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.dataframe(corr_df, use_container_width=True)
        with col_c2:
            fig_heat = px.imshow(
                corr_df,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Viridis",
                title="Subject Inter-Correlation Heatmap",
            )
            fig_heat.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    # Attendance vs Academic Performance Correlation
    att_summary = database.get_attendance_summary()
    if not att_summary.empty:
        merged_att = df.merge(
            att_summary[["student_id", "attendance_percentage"]],
            left_on="id",
            right_on="student_id",
            how="inner",
        ).dropna(subset=["attendance_percentage"])

        if len(merged_att) >= 3:
            st.subheader("Attendance versus Academic Performance Correlation")
            r_val = merged_att["attendance_percentage"].corr(merged_att["Average"])
            st.write(
                f"Statistical Pearson correlation coefficient: **r = {r_val:.3f}**. "
                f"Demonstrates a {'strong positive' if r_val > 0.6 else 'moderate positive' if r_val > 0.3 else 'weak or neutral'} "
                "relationship between class attendance compliance and academic examination scores."
            )

            fig_att_corr = px.scatter(
                merged_att,
                x="attendance_percentage",
                y="Average",
                color="Grade",
                text="name",
                trendline="ols",
                title="Cohort Attendance (%) vs Average Marks Correlation",
                color_discrete_map={
                    "A+": "#38bdf8",
                    "A": "#60a5fa",
                    "B": "#818cf8",
                    "C": "#a78bfa",
                    "D": "#f59e0b",
                    "F": "#ef4444",
                },
            )
            fig_att_corr.update_traces(textposition="top center")
            fig_att_corr.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                xaxis_title="Recorded Attendance (%)",
                yaxis_title="Average Marks",
                xaxis_range=[min(50, merged_att["attendance_percentage"].min() - 5), 105],
                yaxis_range=[0, 105],
            )
            st.plotly_chart(fig_att_corr, use_container_width=True)

    st.divider()

    # 3D Student Marks Coordinate Space
    st.subheader("3D Multi-Student Coordinate Space")
    all_marks = database.get_marks(exam_id=selected_exam_id)
    fig_3d_marks = charts3d.student_marks_surface_3d(all_marks)
    st.plotly_chart(fig_3d_marks, use_container_width=True)

    st.divider()

    # Individual Student Diagnostic
    st.subheader("Individual Student Diagnostic")
    students = database.get_students()

    if not students.empty:
        sel_student_id = st.selectbox(
            "Select Student Profile",
            students["id"].tolist(),
            format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
            key="perf_individual_selector",
        )

        student_row = df[df["id"] == sel_student_id]
        student_marks = all_marks[all_marks["id"] == sel_student_id]

        if not student_row.empty:
            s = student_row.iloc[0]
            col_ind1, col_ind2, col_ind3, col_ind4 = st.columns(4)
            col_ind1.metric("Average Marks", f"{s['Average']:.2f}")
            col_ind2.metric("Grade Category", s["Grade"])
            col_ind3.metric("Institutional Rank", int(s["Rank"]))
            col_ind4.metric("Academic Standing", s["Status"])

            if not student_marks.empty:
                fig_student_sub = px.bar(
                    student_marks,
                    x="subject",
                    y="marks",
                    color="subject",
                    text="marks",
                    title=f"Course Marks for {s['name']}",
                    color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f43f5e"],
                )
                fig_student_sub.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15, 23, 42, 0.6)",
                    yaxis_range=[0, 105],
                    showlegend=False,
                )
                st.plotly_chart(fig_student_sub, use_container_width=True)
