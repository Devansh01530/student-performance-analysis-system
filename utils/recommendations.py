"""
Intelligent Academic Recommendation & Risk Detection Engine.
Provides:
- Shared canonical academic risk classification (Low, Medium, High Risk)
- Rule-based subject-specific diagnostics
- Personalized strengths and weaknesses analysis
- Actionable improvement strategies for individual students and cohorts
"""

import pandas as pd
import database
from utils.analysis import get_student_performance


def classify_student_risk(avg_score: float, status: str, att_pct: float | None = None, weakness_count: int = 0) -> tuple[str, str]:
    """
    Unified, single canonical academic risk classification function.
    Shared identically across individual student recommendations and cohort risk overviews.

    Decision Rules:
    1. High Risk:
       - Status is 'Fail' (scored < 40 in any subject)
       - OR Average < 45.0
       - OR Attendance is recorded and < 70.0%
       Action: Immediate faculty intervention, remedial tutoring, and mandatory attendance monitoring.

    2. Medium Risk:
       - Not High Risk, AND:
       - Average < 65.0
       - OR Weakness count >= 1 (any subject scored < 70.0)
       - OR Attendance is recorded and < 75.0%
       Action: Targeted assignment reviews and supplemental practice sessions.

    3. Low Risk:
       - Pass status, Average >= 65.0, 0 weaknesses, attendance >= 75.0% (or attendance unrecorded).
       Action: Performance on track. Continue balanced study schedule and challenge assignments.

    Boundary Rules:
    - Average == 45.0 with Pass status and good attendance -> Medium Risk (not High Risk)
    - Average == 65.0 with Pass status, 0 weaknesses, good attendance -> Low Risk
    - Attendance == 70.0% -> Medium Risk (not High Risk)
    - Attendance == 75.0% -> Low Risk
    - Missing attendance (None) -> Does NOT penalize the student to High or Medium risk.

    Returns:
    (risk_category, recommended_action)
    """
    is_low_att = (att_pct is not None and att_pct < 70.0)
    is_med_att = (att_pct is not None and att_pct < 75.0)

    if status == "Fail" or avg_score < 45.0 or is_low_att:
        risk_level = "High Risk"
        risk_action = "Immediate faculty intervention, remedial tutoring, and mandatory attendance monitoring."
    elif avg_score < 65.0 or weakness_count >= 1 or is_med_att:
        risk_level = "Medium Risk"
        risk_action = "Targeted assignment reviews and supplemental practice sessions."
    else:
        risk_level = "Low Risk"
        risk_action = "Performance on track. Continue balanced study schedule and challenge assignments."

    return risk_level, risk_action


def generate_student_recommendations(student_id: int, exam_id=None, allow_all=False) -> dict:
    """
    Generates personalized academic diagnosis and recommendations for a single student.
    Evaluates:
    - Overall grade and average for the selected examination scope
    - Subject-by-subject marks
    - Strengths and areas requiring focus
    - Attendance correlation
    - Risk classification using canonical shared rules
    """
    all_marks = database.get_marks(exam_id=exam_id, student_id=student_id)
    perf = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    att_df = database.get_attendance_summary()

    if perf.empty or student_id not in perf["id"].values:
        return {}

    s_row = perf[perf["id"] == student_id].iloc[0]

    student_name = s_row["name"]
    avg_score = float(s_row["Average"])
    grade = s_row["Grade"]
    status = s_row["Status"]
    rank = int(s_row["Rank"])
    exam_scope = s_row.get("Exam_Scope", "Current Examination")

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

    for _, m_row in all_marks.iterrows():
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

    # Classify risk using shared canonical function
    risk_level, risk_action = classify_student_risk(
        avg_score=avg_score,
        status=status,
        att_pct=att_pct,
        weakness_count=len(weaknesses),
    )

    return {
        "id": student_id,
        "name": student_name,
        "exam_scope": exam_scope,
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


def get_cohort_risk_overview(exam_id=None, allow_all=False) -> pd.DataFrame:
    """
    Categorizes all students in the cohort into Low, Medium, or High Risk tiers
    using the shared canonical classify_student_risk() function.
    """
    perf = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    att_df = database.get_attendance_summary()

    if perf.empty:
        return pd.DataFrame()

    meta_cols = ["id", "name", "department", "semester", "Average", "Total", "Grade", "Status", "Rank", "Exam_Scope", "Exam_ID"]
    subject_cols = [c for c in perf.columns if c not in meta_cols]

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

        # Count subjects scored < 70
        weakness_count = 0
        for sub in subject_cols:
            if pd.notna(row[sub]) and float(row[sub]) < 70.0:
                weakness_count += 1

        # Classify risk using unified shared function
        risk_level, _ = classify_student_risk(
            avg_score=avg,
            status=status,
            att_pct=att_pct,
            weakness_count=weakness_count,
        )

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
            "Risk_Category": risk_level,
            "Exam_Scope": row.get("Exam_Scope", "Evaluated Scope"),
        })

    return pd.DataFrame(results).sort_values("Rank")
