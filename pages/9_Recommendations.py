import streamlit as st
import pandas as pd
import plotly.express as px

import database
from utils.analysis import get_student_performance
from utils.recommendations import generate_student_recommendations, get_cohort_risk_overview
from utils.report_generator import generate_student_report_card_pdf
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Academic Recommendations",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Personalized Academic Recommendations")
st.write(
    "Automated academic intelligence: rule-based subject diagnostics, personalized strength/weakness evaluations, and cohort risk detection."
)

st.divider()

perf = get_student_performance()
students = database.get_students()

if perf.empty or students.empty:
    st.info("No student academic records available for diagnostic recommendations.")
else:
    # Cohort Risk Stratification Overview
    st.subheader("Cohort Academic Risk Stratification")

    cohort_risk = get_cohort_risk_overview()

    col_r1, col_r2, col_r3 = st.columns(3)
    high_risk_count = len(cohort_risk[cohort_risk["Risk_Category"] == "High Risk"])
    med_risk_count = len(cohort_risk[cohort_risk["Risk_Category"] == "Medium Risk"])
    low_risk_count = len(cohort_risk[cohort_risk["Risk_Category"] == "Low Risk"])

    col_r1.metric("Low Risk (On Track)", low_risk_count)
    col_r2.metric("Medium Risk (Attention Needed)", med_risk_count)
    col_r3.metric("High Risk (Critical Intervention)", high_risk_count)

    # Risk Distribution Donut
    risk_summary = cohort_risk["Risk_Category"].value_counts().reset_index()
    risk_summary.columns = ["Risk_Category", "Count"]

    fig_risk_pie = px.pie(
        risk_summary,
        names="Risk_Category",
        values="Count",
        hole=0.55,
        title="Cohort Academic Risk Tier Breakdown",
        color="Risk_Category",
        color_discrete_map={
            "Low Risk": "#10b981",
            "Medium Risk": "#f59e0b",
            "High Risk": "#ef4444",
        },
    )
    fig_risk_pie.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
    )
    st.plotly_chart(fig_risk_pie, use_container_width=True)

    # Risk Table
    st.dataframe(
        cohort_risk[[
            "Rank", "name", "department", "semester", "Average", "Grade", "Status", "Attendance_Pct", "Risk_Category"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Individual Student Diagnostic & Personalized Guidance
    st.subheader("Individual Student Diagnostic & Remedial Roadmap")

    selected_student_id = st.selectbox(
        "Select Student for Diagnostic Evaluation",
        students["id"].tolist(),
        format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
    )

    rec = generate_student_recommendations(selected_student_id)

    if rec:
        # Overview Cards
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Cohort Rank", rec["rank"])
        o2.metric("Mean Average Score", f"{rec['average']:.2f}")
        o3.metric("Grade Category", rec["grade"])
        o4.metric("Assessed Risk Tier", rec["risk_level"])

        # Risk Banner
        banner_border = "#ef4444" if rec["risk_level"] == "High Risk" else "#f59e0b" if rec["risk_level"] == "Medium Risk" else "#10b981"
        st.markdown(
            f"""
            <div class="card-3d" style="border-left: 5px solid {banner_border}; margin-top: 14px;">
                <div style="font-size: 0.8rem; text-transform: uppercase; color: {banner_border}; font-weight: 700;">
                    Overall Remedial Directive
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: #ffffff; margin-top: 4px;">
                    {rec['risk_action']}
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 6px;">
                    Attendance Rate: <b>{rec['attendance']:.1f}%</b> | Standing: <b>{rec['status']}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Strengths & Weaknesses
        st.subheader("Academic Competency Profile")
        col_st1, col_st2 = st.columns(2)

        with col_st1:
            st.markdown(
                """
                <div class="card-3d">
                    <div style="font-size: 0.85rem; text-transform: uppercase; color: #10b981; font-weight: 700;">Core Academic Strengths</div>
                """,
                unsafe_allow_html=True,
            )
            for s in rec["strengths"]:
                st.write(f"- **{s}**")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_st2:
            st.markdown(
                """
                <div class="card-3d">
                    <div style="font-size: 0.85rem; text-transform: uppercase; color: #f43f5e; font-weight: 700;">Target Focus Areas</div>
                """,
                unsafe_allow_html=True,
            )
            for w in rec["weaknesses"]:
                st.write(f"- **{w}**")
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # Subject-by-Subject Remedial Table
        st.subheader("Course-Specific Recommendations")

        subj_recs_df = pd.DataFrame(rec["subjects"])
        st.dataframe(
            subj_recs_df[["subject", "marks", "category", "advice"]],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # Export Report Card PDF
        st.subheader("Export Student Diagnostic Report Card")
        pdf_card = generate_student_report_card_pdf(selected_student_id)

        st.download_button(
            label=f"Download Official Report Card (PDF) - {rec['name']}",
            data=pdf_card,
            file_name=f"report_card_student_{selected_student_id}.pdf",
            mime="application/pdf",
        )

