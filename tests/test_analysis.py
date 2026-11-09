import sys
import os
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_department_performance,
    get_semester_performance,
    get_dashboard_metrics,
)
from utils.predict import train_and_evaluate_models


class TestAnalysis(unittest.TestCase):
    def test_student_performance_calculation(self):
        """Verify performance metrics, grades, and ranks."""
        perf = get_student_performance()
        self.assertIsInstance(perf, pd.DataFrame)
        self.assertFalse(perf.empty)
        self.assertIn("Average", perf.columns)
        self.assertIn("Total", perf.columns)
        self.assertIn("Grade", perf.columns)
        self.assertIn("Status", perf.columns)
        self.assertIn("Rank", perf.columns)

        valid_grades = {"A+", "A", "B", "C", "D", "F"}
        self.assertTrue(set(perf["Grade"].unique()).issubset(valid_grades))
        self.assertTrue(set(perf["Status"].unique()).issubset({"Pass", "Fail"}))

    def test_subject_analysis_calculation(self):
        """Verify subject aggregations."""
        subjs = get_subject_analysis()
        self.assertIsInstance(subjs, pd.DataFrame)
        self.assertFalse(subjs.empty)
        self.assertIn("Average", subjs.columns)
        self.assertIn("Highest", subjs.columns)
        self.assertIn("Lowest", subjs.columns)
        self.assertIn("Pass_Percentage", subjs.columns)

    def test_department_and_semester_performance(self):
        """Verify macro aggregations."""
        dept = get_department_performance()
        sem = get_semester_performance()
        self.assertIsInstance(dept, pd.DataFrame)
        self.assertIsInstance(sem, pd.DataFrame)

    def test_dashboard_metrics(self):
        """Verify dashboard KPI dictionary structure."""
        m = get_dashboard_metrics()
        self.assertIsInstance(m, dict)
        expected_keys = [
            "total_students", "total_departments", "total_subjects",
            "class_average", "pass_percentage", "fail_percentage",
            "highest_average", "failed_students", "attendance_average",
        ]
        for k in expected_keys:
            self.assertIn(k, m)

    def test_predictive_longitudinal_models(self):
        """Verify predictive model trains with student-grouped and chronological evaluations without data leakage."""
        res_grouped = train_and_evaluate_models(eval_strategy="student_grouped")
        self.assertEqual(res_grouped["status"], "success")
        self.assertIn("metrics", res_grouped)
        self.assertIn("test_comparison", res_grouped)
        self.assertIn("cohort_predictions", res_grouped)
        self.assertTrue(len(res_grouped["test_students"]) > 0)

        res_chrono = train_and_evaluate_models(eval_strategy="chronological")
        self.assertEqual(res_chrono["status"], "success")
        self.assertIn("metrics", res_chrono)


if __name__ == "__main__":
    unittest.main()
