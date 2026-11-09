import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

import database
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Attendance Management",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Attendance Management System")
st.write(
    "Integrated attendance tracking: log daily attendance, calculate attendance percentages, monitor compliance thresholds, and evaluate academic risk."
)

st.divider()

students = database.get_students()
att_summary = database.get_attendance_summary()

if students.empty:
    st.info("No enrolled students found.")
else:
    # Configurable Attendance Threshold
    col_th1, col_th2 = st.columns([1, 2])
    with col_th1:
        threshold_val = st.slider("Minimum Required Attendance Threshold (%)", 50.0, 95.0, 75.0, step=1.0)

    # Recalculate status based on slider
    if not att_summary.empty:
        def evaluate_status(row):
            if row["total_classes"] == 0 or pd.isna(row["attendance_percentage"]):
                return "Not Recorded"
            return "Normal" if row["attendance_percentage"] >= threshold_val else "Low Attendance"

        att_summary["attendance_status"] = att_summary.apply(evaluate_status, axis=1)
        total_enrolled = len(att_summary)
        low_att_students = att_summary[att_summary["attendance_status"] == "Low Attendance"]
        normal_att_students = att_summary[att_summary["attendance_status"] == "Normal"]
        unrecorded_students = att_summary[att_summary["attendance_status"] == "Not Recorded"]

        # Calculate mean excluding unrecorded students
        recorded_series = att_summary["attendance_percentage"].dropna()
        if not recorded_series.empty:
            mean_att_display = f"{recorded_series.mean():.2f}%"
        else:
            mean_att_display = "Not Recorded"

        # Overview Metrics
        st.subheader("Attendance Health Overview")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Enrolled Cohort", total_enrolled)
        a2.metric("Mean Attendance Rate", mean_att_display)
        a3.metric("Compliant Count", len(normal_att_students))
        a4.metric("Non-Compliant Count", len(low_att_students))

        # Alert Callout for Non-Compliant Students
        if not low_att_students.empty:
            st.markdown(
                f"""
                <div class="card-3d" style="border-left: 4px solid #f43f5e; margin-bottom: 20px;">
                    <div style="font-size: 0.82rem; text-transform: uppercase; color: #f43f5e; font-weight: 700;">
                        Attendance Compliance Alert
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 600; color: #ffffff; margin-top: 4px;">
                        {len(low_att_students)} Student(s) Below {threshold_val}% Attendance Threshold
                    </div>
                    <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 6px;">
                        Immediate administrative notice recommended. Non-compliant attendance significantly correlates with academic examination failure.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not unrecorded_students.empty:
            st.info(f"{len(unrecorded_students)} student(s) have no attendance logged yet and are categorized as 'Not Recorded' (excluded from the cohort average).")

        st.divider()

        # Visual Attendance Distribution
        st.subheader("Attendance Distribution Profiles")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            plot_df = att_summary.copy()
            plot_df["display_pct"] = plot_df["attendance_percentage"].fillna(0)
            plot_df["text_label"] = plot_df["attendance_percentage"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "Not Recorded")

            fig_att_bar = px.bar(
                plot_df,
                x="name",
                y="display_pct",
                color="attendance_status",
                text="text_label",
                title="Student Attendance Percentages",
                color_discrete_map={"Normal": "#10b981", "Low Attendance": "#ef4444", "Not Recorded": "#64748b"},
            )
            fig_att_bar.add_hline(y=threshold_val, line_dash="dash", line_color="#f59e0b", annotation_text=f"Threshold ({threshold_val}%)")
            fig_att_bar.update_traces(textposition="outside")
            fig_att_bar.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                yaxis_range=[0, 115],
                xaxis_title="Student",
                yaxis_title="Attendance (%)",
            )
            st.plotly_chart(fig_att_bar, use_container_width=True)

        with col_g2:
            status_counts = att_summary["attendance_status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_att_pie = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.55,
                title="Compliance Distribution",
                color="Status",
                color_discrete_map={"Normal": "#10b981", "Low Attendance": "#ef4444", "Not Recorded": "#64748b"},
            )
            fig_att_pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
            )
            st.plotly_chart(fig_att_pie, use_container_width=True)

        st.divider()

        # Detailed Attendance Summary Table
        st.subheader("Student Attendance Registry")
        table_view = att_summary[[
            "student_id", "name", "department", "semester", "total_classes", "classes_attended", "attendance_percentage", "attendance_status"
        ]].copy()
        table_view["attendance_percentage"] = table_view["attendance_percentage"].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "Not Recorded")
        st.dataframe(
            table_view,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # Log New Daily Attendance Record
    st.subheader("Record Daily Class Attendance")

    with st.form("record_attendance_form"):
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            att_student_id = st.selectbox(
                "Enrolled Student",
                students["id"].tolist(),
                format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
            )
        with col_r2:
            att_subject = st.selectbox("Course Subject", ["Python", "C++", "Java", "Data Structures", "Database Management"])
        with col_r3:
            att_date = st.date_input("Attendance Date", value=datetime.today())

        att_status = st.radio("Status", ["Present", "Absent"], horizontal=True)

        submit_att = st.form_submit_button("Record Attendance Entry")

        if submit_att:
            database.record_attendance(
                att_student_id,
                att_subject,
                str(att_date),
                att_status,
            )
            st.success(f"Recorded '{att_status}' for ID {att_student_id} on {att_date}.")
            st.rerun()

    st.divider()

    # Log Filter & Historical Daily Sheet
    st.subheader("Historical Attendance Log")

    col_fl1, col_fl2 = st.columns(2)
    with col_fl1:
        hist_subj = st.selectbox("Filter Subject", ["All", "Python", "C++", "Java", "Data Structures", "Database Management"])
    with col_fl2:
        hist_std = st.selectbox(
            "Filter Student",
            [("All Students", None)] + [(r["name"], r["id"]) for _, r in students.iterrows()],
            format_func=lambda x: x[0],
        )

    raw_logs = database.get_attendance(
        student_id=hist_std[1],
        subject=hist_subj,
    )

    if raw_logs.empty:
        st.info("No matching daily attendance logs.")
    else:
        st.dataframe(
            raw_logs[["attendance_date", "name", "subject", "status", "department", "semester"]],
            use_container_width=True,
            hide_index=True,
        )

