import streamlit as st
import database
from utils.analysis import get_dashboard_metrics
from utils.style import apply_custom_css, add_sidebar_branding

# Page configuration
st.set_page_config(
    page_title="Student Performance Analysis System",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_custom_css()
add_sidebar_branding()

# Create database tables and reference migrations
database.create_tables()

# 3D Main Hero Header
st.markdown(
    """
    <div class="card-3d" style="padding: 28px 32px; margin-bottom: 24px;">
        <div style="font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.16em; color: #38bdf8; font-weight: 700;">
            Academic Performance Intelligence Platform
        </div>
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 2.2rem; font-weight: 700; color: #ffffff; margin-top: 6px;">
            Student Performance Analysis System
        </div>
        <div style="font-size: 0.98rem; color: #94a3b8; margin-top: 8px; max-width: 860px; line-height: 1.6;">
            A unified institutional intelligence platform answering four critical questions:
            <b>What is happening?</b> via real-time analytical dashboards;
            <b>Why is it happening?</b> through subject diagnostics and attendance correlation;
            <b>What might happen next?</b> using Machine Learning regression forecasting; and
            <b>What should be done?</b> via personalized remedial recommendations and risk detection.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Dashboard statistics
metrics = get_dashboard_metrics()

st.subheader("Institutional Performance Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Enrolled Cohort", metrics["total_students"])
col2.metric("Institution Mean", f"{metrics['class_average']:.2f}")
col3.metric("Pass Rate", f"{metrics['pass_percentage']}%")
col4.metric("At-Risk Students", metrics["failed_students"])

st.divider()

# Core Architecture Modules Matrix
st.subheader("Platform Functional Modules")

col_m1, col_m2 = st.columns(2)

with col_m1:
    st.markdown(
        """
        <div class="card-3d">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                1. Executive Dashboard
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Overview metrics, multi-axis distributions, 3D spatial performance charts, and cohort leaders.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Dashboard.py", label="Open Executive Dashboard")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                2. Student Management System
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Full CRUD control: enroll students, search profiles, edit details, and record marks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Student_Management.py", label="Open Student Management")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                3. Performance Analysis
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Cohort ranking, letter grade calculations, subject correlation heatmaps, and filtering.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Performance_Analysis.py", label="Open Performance Analysis")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                4. Subject Diagnostics
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Curriculum difficulty evaluations, 3D subject landscape, and score extremes.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_Subject_Analysis.py", label="Open Subject Diagnostics")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                5. Reports and Data Export
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Generate official PDF reports, individual report cards, CSVs, and multi-sheet Excel workbooks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/5_Reports.py", label="Open Reports Center")

with col_m2:
    st.markdown(
        """
        <div class="card-3d">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                6. Predictive Analytics and Machine Learning
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Linear, Decision Tree, and Random Forest regression models, holdout evaluation, and What-If simulator.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/6_Predictive_Analytics.py", label="Open Predictive Analytics")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                7. Academic Progress Tracking
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Longitudinal tracking across Internal 1, Internal 2, Mid-Semester, and Final Examinations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/7_Academic_Progress.py", label="Open Academic Progress")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                8. Attendance Management System
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Log daily attendance, compute compliance rates, and trigger non-compliance alerts (< 75%).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/8_Attendance_Management.py", label="Open Attendance Management")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                9. Personalized Recommendations
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Rule-based improvement recommendations, strengths/weaknesses profiling, and risk tiers.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/9_Recommendations.py", label="Open Recommendations")

    st.markdown(
        """
        <div class="card-3d" style="margin-top: 14px;">
            <div style="font-size: 1.15rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">
                10. Data Import and Cleaning
            </div>
            <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;">
                Upload CSV and Excel files, run automated Pandas data cleaning pipelines, and commit to SQLite.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/10_Data_Import.py", label="Open Data Import Pipeline")

st.divider()

# Maintenance & Backup
st.subheader("Database Maintenance & Snapshot Backup")
col_b1, col_b2 = st.columns([1, 2])
with col_b1:
    if st.button("Generate Database Snapshot Backup"):
        dest = database.backup_database()
        st.success(f"Snapshot backup created: {dest}")

st.caption("Student Performance System | Institutional Academic Intelligence Platform")
