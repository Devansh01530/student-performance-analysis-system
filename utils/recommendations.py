"""
Intelligent Academic Recommendation & Risk Detection Engine.
Provides:
- Rule-based subject-specific diagnostics
- Personalized strengths and weaknesses analysis
- Academic risk classification (Low, Medium, High Risk)
- Actionable improvement strategies for individual students and cohorts
"""

import pandas as pd
import database
from utils.analysis import get_student_performance


def generate_student_recommendations(student_id: int) -> dict:
    """
    Generates personalized academic diagnosis and recommendations for a single student.
    Evaluates:
    - Overall grade and average
    - Subject-by-subject marks
    - Strengths and areas requiring focus
    - Attendance correlation
    - Risk classification
    """
    students = database.get_students()
    all_marks = database.get_marks()
    perf = get_student_performance()
    att_df = database.get_attendance_summary()

    if perf.empty or student_id not in perf["id"].values:
        return {}

    s_row = perf[perf["id"] == student_id].iloc[0]
    s_marks = all_marks[all_marks["id"] == student_id]

    student_name = s_row["name"]
    avg_score = float(s_row["Average"])
    grade = s_row["Grade"]
    status = s_row["Status"]
    rank = int(s_row["Rank"])

    # Attendance (None if not recorded)
    att_pct = None
    if not att_df.empty and student_id in att_df["student_id"].values:
        val = att_df[att_df["student_id"] == student_id].iloc[0]["attendance_percentage"]
        if pd.notna(val) and val is not None:
            att_pct = float(val)

    # Subject evaluations
    subject_diagnostics = []
    strengths = []
    weaknesses = []

    for _, m_row in s_marks.iterrows():
        subj = m_row["subject"]
        score = float(m_row["marks"])

        if score >= 80.0:
            category = "Excellent Performance"
            advice = "Outstanding mastery. Maintain consistency and mentor peer cohorts."
            strengths.append(subj)
        elif score >= 70.0:
            category = "Good Performance"
            advice = "Strong foundation demonstrated. Target advanced concept application."
            strengths.append(subj)
        elif score >= 50.0:
            category = "Needs Improvement"
            advice = "Moderate grasp. Recommend structured revision and problem-solving practice."
            weaknesses.append(subj)
        else:
            category = "Immediate Attention Required"
            advice = "High priority: Scored below passing or mastery threshold. Remedial tutorials recommended."
            weaknesses.append(subj)

        subject_diagnostics.append({
            "subject": subj,
            "marks": score,
            "category": category,
            "advice": advice,
        })

    # Overall Risk Level
    # Rules: Fail status or avg < 45 or recorded attendance < 70% -> High Risk
    # Avg between 45 and 65 or 1 weakness or recorded attendance < 75% -> Medium Risk
    # Else Low Risk
    is_low_att = (att_pct is not None and att_pct < 70.0)
    is_med_att = (att_pct is not None and att_pct < 75.0)

    if status == "Fail" or avg_score < 45.0 or is_low_att:
        risk_level = "High Risk"
        risk_action = "Immediate faculty intervention, remedial tutoring, and mandatory attendance monitoring."
    elif avg_score < 65.0 or len(weaknesses) >= 1 or is_med_att:
        risk_level = "Medium Risk"
        risk_action = "Targeted assignment reviews and supplemental practice sessions."
    else:
        risk_level = "Low Risk"
        risk_action = "Performance on track. Continue balanced study schedule and challenge assignments."

    return {
        "id": student_id,
        "name": student_name,
        "average": avg_score,
        "grade": grade,
        "rank": rank,
        "status": status,
        "attendance": att_pct,
        "risk_level": risk_level,
        "risk_action": risk_action,
        "strengths": strengths if strengths else ["Consistent across syllabus"],
        "weaknesses": weaknesses if weaknesses else ["No critical deficiency"],
        "subjects": subject_diagnostics,
    }


def get_cohort_risk_overview() -> pd.DataFrame:
    """
    Categorizes all students in the cohort into Low, Medium, or High Risk tiers.
    """
    perf = get_student_performance()
    att_df = database.get_attendance_summary()

    if perf.empty:
        return pd.DataFrame()

    results = []
    for _, row in perf.iterrows():
        s_id = row["id"]
        avg = float(row["Average"])
        status = row["Status"]

        att_pct = None
        if not att_df.empty and s_id in att_df["student_id"].values:
            val = att_df[att_df["student_id"] == s_id].iloc[0]["attendance_percentage"]
            if pd.notna(val) and val is not None:
                att_pct = float(val)

        is_low_att = (att_pct is not None and att_pct < 70.0)
        is_med_att = (att_pct is not None and att_pct < 75.0)

        if status == "Fail" or avg < 45.0 or is_low_att:
            risk = "High Risk"
        elif avg < 65.0 or is_med_att:
            risk = "Medium Risk"
        else:
            risk = "Low Risk"

        results.append({
            "Rank": int(row["Rank"]),
            "id": s_id,
            "name": row["name"],
            "department": row["department"],
            "semester": int(row["semester"]),
            "Average": avg,
            "Grade": row["Grade"],
            "Status": status,
            "Attendance_Pct": f"{att_pct:.1f}%" if att_pct is not None else "Not Recorded",
            "Risk_Category": risk,
        })

    return pd.DataFrame(results).sort_values("Rank")

