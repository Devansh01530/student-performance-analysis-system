import pandas as pd
import numpy as np
import database


def resolve_examination(exam_id=None, allow_all=False):
    """
    Resolves the examination scope:
    - If exam_id is specified: returns (exam_id, exam_name)
    - If exam_id is None and allow_all is False: resolves to the latest valid examination
    - If exam_id is None and allow_all is True: returns (None, 'Cumulative Across All Examinations')
    """
    exams = database.get_examinations()
    if exams.empty:
        return None, "No Examinations"

    if exam_id is not None:
        matched = exams[exams["id"] == exam_id]
        if not matched.empty:
            return exam_id, str(matched.iloc[0]["name"])
        return exam_id, f"Examination {exam_id}"

    if allow_all:
        return None, "Cumulative Across All Examinations"

    # Default to latest examination by exam_date, then id
    exams_sorted = exams.copy()
    exams_sorted["parsed_date"] = pd.to_datetime(exams_sorted["exam_date"], errors="coerce")
    exams_sorted = exams_sorted.sort_values(by=["parsed_date", "id"], na_position="first")
    latest = exams_sorted.iloc[-1]
    return int(latest["id"]), str(latest["name"])


def get_student_performance(exam_id=None, allow_all=False):
    """
    Calculates comprehensive student performance metrics for a specific examination scope.
    Guarantees that marks from different examinations are not unintentionally averaged.
    - If exam_id is provided: evaluates strictly that examination.
    - If exam_id is None and allow_all is False (default): evaluates strictly the latest examination.
    - If exam_id is None and allow_all is True: intentionally computes cumulative average,
      explicitly labeled as 'Cumulative Across All Examinations'.
    """
    target_exam_id, target_exam_name = resolve_examination(exam_id, allow_all)

    if target_exam_id is None and not allow_all:
        return pd.DataFrame()

    marks = database.get_marks(exam_id=target_exam_id)

    if marks.empty:
        return pd.DataFrame()

    # Convert subject records into columns
    df = marks.pivot_table(
        index=["id", "name", "department", "semester"],
        columns="subject",
        values="marks",
        aggfunc="mean",
    ).reset_index()

    df.columns.name = None

    # Identify subject columns
    subject_cols = [
        col for col in df.columns
        if col not in ["id", "name", "department", "semester"]
    ]

    if not subject_cols:
        return pd.DataFrame()

    # Calculate Average and Total
    df["Average"] = df[subject_cols].mean(axis=1).round(2)
    df["Total"] = df[subject_cols].sum(axis=1).round(2)

    # Standard Grade Assignment:
    # A+: 90-100, A: 80-89, B: 70-79, C: 60-69, D: 50-59, F: <50
    def assign_grade(avg):
        if avg >= 90.0:
            return "A+"
        elif avg >= 80.0:
            return "A"
        elif avg >= 70.0:
            return "B"
        elif avg >= 60.0:
            return "C"
        elif avg >= 50.0:
            return "D"
        else:
            return "F"

    df["Grade"] = df["Average"].apply(assign_grade)

    # Pass/Fail: threshold >= 40 across all evaluated subjects
    df["Status"] = df[subject_cols].ge(40.0).all(axis=1).map(
        {True: "Pass", False: "Fail"}
    )

    # Dense Ranking by Average Score
    df["Rank"] = df["Average"].rank(method="dense", ascending=False).astype(int)

    # Attach explicit examination metadata
    df["Exam_Scope"] = target_exam_name
    if target_exam_id is not None:
        df["Exam_ID"] = target_exam_id

    return df.sort_values("Rank")


def get_top_students(limit=5, exam_id=None, allow_all=False):
    """Returns top performing students for a specific examination scope."""
    df = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    return df.head(limit) if not df.empty else df


def get_weak_students(threshold=40.0, exam_id=None, allow_all=False):
    """Returns students needing academic intervention for a specific examination scope."""
    df = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    if df.empty:
        return df
    return df[(df["Average"] < threshold) | (df["Status"] == "Fail")]


def get_subject_analysis(exam_id=None, allow_all=False):
    """
    Computes subject statistics for a specific examination scope:
    - Average marks
    - Highest & Lowest marks
    - Pass percentage (marks >= 40)
    - Fail percentage
    - Enrolled student count
    - Difficulty rating
    """
    target_exam_id, target_exam_name = resolve_examination(exam_id, allow_all)

    if target_exam_id is None and not allow_all:
        return pd.DataFrame()

    marks = database.get_marks(exam_id=target_exam_id)
    if marks.empty:
        return pd.DataFrame()

    def calc_subject_stats(group):
        total = len(group)
        passed = (group["marks"] >= 40.0).sum()
        pass_pct = round((passed / total) * 100, 2) if total > 0 else 0.0
        avg_score = round(group["marks"].mean(), 2)

        # Subject Difficulty rating based on class average
        if avg_score >= 80:
            difficulty = "Easy"
        elif avg_score >= 65:
            difficulty = "Moderate"
        elif avg_score >= 50:
            difficulty = "Challenging"
        else:
            difficulty = "High Difficulty"

        return pd.Series({
            "Average": avg_score,
            "Highest": round(group["marks"].max(), 2),
            "Lowest": round(group["marks"].min(), 2),
            "Pass_Percentage": pass_pct,
            "Fail_Percentage": round(100.0 - pass_pct, 2),
            "Students": total,
            "Difficulty": difficulty,
            "Exam_Scope": target_exam_name,
        })

    result = marks.groupby("subject").apply(calc_subject_stats, include_groups=False).reset_index()
    return result.sort_values(by="Average", ascending=False)


def get_department_performance(exam_id=None, allow_all=False):
    """Calculates performance aggregated by department for a specific examination scope."""
    perf = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    if perf.empty:
        return pd.DataFrame()

    dept_stats = perf.groupby("department").agg(
        Students=("id", "count"),
        Average=("Average", "mean"),
        Highest=("Average", "max"),
        Passed=("Status", lambda s: (s == "Pass").sum()),
    ).reset_index()

    dept_stats["Average"] = dept_stats["Average"].round(2)
    dept_stats["Highest"] = dept_stats["Highest"].round(2)
    dept_stats["Pass_Rate"] = (
        (dept_stats["Passed"] / dept_stats["Students"]) * 100
    ).round(2)
    return dept_stats.sort_values(by="Average", ascending=False)


def get_semester_performance(exam_id=None, allow_all=False):
    """Calculates performance aggregated by semester for a specific examination scope."""
    perf = get_student_performance(exam_id=exam_id, allow_all=allow_all)
    if perf.empty:
        return pd.DataFrame()

    sem_stats = perf.groupby("semester").agg(
        Students=("id", "count"),
        Average=("Average", "mean"),
        Highest=("Average", "max"),
        Passed=("Status", lambda s: (s == "Pass").sum()),
    ).reset_index()

    sem_stats["Average"] = sem_stats["Average"].round(2)
    sem_stats["Highest"] = sem_stats["Highest"].round(2)
    sem_stats["Pass_Rate"] = (
        (sem_stats["Passed"] / sem_stats["Students"]) * 100
    ).round(2)
    return sem_stats.sort_values(by="semester")


def get_subject_correlation(exam_id=None, allow_all=False):
    """
    Computes correlation matrix between subject marks for a specific examination scope.
    Returns correlation DataFrame.
    """
    target_exam_id, _ = resolve_examination(exam_id, allow_all)
    marks = database.get_marks(exam_id=target_exam_id)
    if marks.empty:
        return pd.DataFrame()

    pivot = marks.pivot_table(
        index="id",
        columns="subject",
        values="marks",
        aggfunc="mean",
    )
    return pivot.corr().round(3)


def get_attendance_analytics():
    """Returns summarized attendance distribution and metrics, excluding unrecorded students from the average."""
    att = database.get_attendance_summary()
    if att.empty:
        return {
            "overall_average": None,
            "overall_display": "Not Recorded",
            "low_attendance_count": 0,
            "normal_attendance_count": 0,
            "unrecorded_count": 0,
            "records": att,
        }

    # Strictly exclude students who have no recorded attendance classes from the cohort average
    recorded_att = att[att["total_classes"] > 0]
    if not recorded_att.empty and recorded_att["attendance_percentage"].notna().any():
        overall_avg = round(float(recorded_att["attendance_percentage"].dropna().mean()), 2)
        overall_display = f"{overall_avg:.2f}%"
    else:
        overall_avg = None
        overall_display = "Not Recorded"

    low_att = len(att[att["attendance_status"] == "Low Attendance"])
    normal_att = len(att[att["attendance_status"] == "Normal"])
    unrecorded_att = len(att[att["attendance_status"] == "Not Recorded"])

    return {
        "overall_average": overall_avg,
        "overall_display": overall_display,
        "low_attendance_count": low_att,
        "normal_attendance_count": normal_att,
        "unrecorded_count": unrecorded_att,
        "records": att,
    }


def get_dashboard_metrics(exam_id=None, allow_all=False):
    """Comprehensive KPIs for Executive Dashboard for a specific examination scope."""
    target_exam_id, target_exam_name = resolve_examination(exam_id, allow_all)
    students = database.get_students()
    performance = get_student_performance(exam_id=target_exam_id, allow_all=allow_all)
    subjects = get_subject_analysis(exam_id=target_exam_id, allow_all=allow_all)
    departments = database.get_departments()
    att_analytics = get_attendance_analytics()

    if performance.empty:
        return {
            "exam_scope": target_exam_name,
            "total_students": len(students),
            "total_departments": len(departments) if not departments.empty else 1,
            "total_subjects": len(subjects) if not subjects.empty else 0,
            "class_average": 0.0,
            "pass_percentage": 0.0,
            "fail_percentage": 0.0,
            "highest_average": 0.0,
            "failed_students": 0,
            "attendance_average": att_analytics["overall_display"],
            "low_attendance_count": att_analytics["low_attendance_count"],
            "unrecorded_attendance_count": att_analytics["unrecorded_count"],
            "strongest_subject": "N/A",
            "weakest_subject": "N/A",
        }

    total = len(performance)
    passed = len(performance[performance["Status"] == "Pass"])
    failed = total - passed
    pass_pct = round((passed / total) * 100, 2)
    fail_pct = round((failed / total) * 100, 2)

    strongest = subjects.iloc[0]["subject"] if not subjects.empty else "N/A"
    weakest = subjects.iloc[-1]["subject"] if not subjects.empty else "N/A"

    return {
        "exam_scope": target_exam_name,
        "total_students": len(students),
        "total_departments": len(performance["department"].unique()),
        "total_subjects": len(subjects) if not subjects.empty else 0,
        "class_average": round(float(performance["Average"].mean()), 2),
        "pass_percentage": pass_pct,
        "fail_percentage": fail_pct,
        "highest_average": round(float(performance["Average"].max()), 2),
        "failed_students": failed,
        "attendance_average": att_analytics["overall_display"],
        "low_attendance_count": att_analytics["low_attendance_count"],
        "unrecorded_attendance_count": att_analytics["unrecorded_count"],
        "strongest_subject": strongest,
        "weakest_subject": weakest,
    }
