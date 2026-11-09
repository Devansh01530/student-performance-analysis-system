import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_department_performance,
    get_semester_performance,
    get_subject_correlation,
    get_dashboard_metrics,
)


def test_student_performance_calculation():
    """Verify performance metrics, grades, and ranks."""
    perf = get_student_performance()
    assert isinstance(perf, pd.DataFrame)
    assert not perf.empty
    assert "Average" in perf.columns
    assert "Total" in perf.columns
    assert "Grade" in perf.columns
    assert "Status" in perf.columns
    assert "Rank" in perf.columns

    # Verify grade validity
    valid_grades = {"A+", "A", "B", "C", "D", "F"}
    assert set(perf["Grade"].unique()).issubset(valid_grades)

    # Verify status
    assert set(perf["Status"].unique()).issubset({"Pass", "Fail"})


def test_subject_analysis_calculation():
    """Verify subject aggregations."""
    subjs = get_subject_analysis()
    assert isinstance(subjs, pd.DataFrame)
    assert not subjs.empty
    assert "Average" in subjs.columns
    assert "Highest" in subjs.columns
    assert "Lowest" in subjs.columns
    assert "Pass_Percentage" in subjs.columns


def test_department_and_semester_performance():
    """Verify macro aggregations."""
    dept = get_department_performance()
    sem = get_semester_performance()
    assert isinstance(dept, pd.DataFrame)
    assert isinstance(sem, pd.DataFrame)


def test_dashboard_metrics():
    """Verify dashboard KPI dictionary structure."""
    m = get_dashboard_metrics()
    assert isinstance(m, dict)
    expected_keys = [
        "total_students", "total_departments", "total_subjects",
        "class_average", "pass_percentage", "fail_percentage",
        "highest_average", "failed_students", "attendance_average",
    ]
    for k in expected_keys:
        assert k in m


def test_predictive_longitudinal_models():
    """Verify predictive model trains on longitudinal examination transitions without data leakage."""
    from utils.predict import train_and_evaluate_models
    res = train_and_evaluate_models()
    assert res["status"] == "success"
    assert "metrics" in res
    assert "test_comparison" in res
    assert "cohort_predictions" in res

    metrics_df = res["metrics"]
    assert "MAE" in metrics_df.columns
    assert "RMSE" in metrics_df.columns
    assert "R2_Score" in metrics_df.columns


if __name__ == "__main__":
    print("Running analysis tests...")
    test_student_performance_calculation()
    test_subject_analysis_calculation()
    test_department_and_semester_performance()
    test_dashboard_metrics()
    test_predictive_longitudinal_models()
    print("Analysis tests passed successfully.")
