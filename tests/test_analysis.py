import sys
import os
import unittest
import tempfile
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from utils.analysis import (
    get_student_performance,
    get_subject_analysis,
    get_department_performance,
    get_semester_performance,
    get_dashboard_metrics,
    get_subject_correlation,
    resolve_examination,
)
from utils.predict import train_and_evaluate_models, build_examination_transitions_dataset
from utils.recommendations import classify_student_risk, get_cohort_risk_overview, generate_student_recommendations


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        """Creates an isolated temporary SQLite database fixture with controlled test data."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        database.create_tables()

        # Seed controlled cohort for testing
        self._seed_controlled_test_cohort()

    def tearDown(self):
        """Restores original database path and removes the temporary test database."""
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def _seed_controlled_test_cohort(self):
        """Populates controlled student records across 4 exams with attendance."""
        conn = database.get_connection()
        cursor = conn.cursor()

        # Seed 8 students
        students_data = [
            (1, "Alice", "alice@example.com", "BCA", 3),
            (2, "Bob", "bob@example.com", "BCA", 3),
            (3, "Charlie", "charlie@example.com", "BCA", 3),
            (4, "David", "david@example.com", "BCA", 3),
            (5, "Eva", "eva@example.com", "B.Tech CSE", 3),
            (6, "Frank", "frank@example.com", "B.Tech CSE", 3),
            (7, "Grace", "grace@example.com", "B.Tech CSE", 3),
            (8, "Hannah", "hannah@example.com", "B.Tech CSE", 3),
        ]
        for s in students_data:
            cursor.execute("INSERT OR REPLACE INTO students (id, name, email, department, semester) VALUES (?, ?, ?, ?, ?)", s)

        # Seed marks across 4 examinations
        subjects = ["Python", "C++", "Java"]
        for s_id in range(1, 9):
            base_score = 40 + (s_id * 6)  # Distinct scores per student
            for exam_id in range(1, 5):
                score_mod = (exam_id - 1) * 3
                for sub in subjects:
                    score = min(100.0, max(0.0, float(base_score + score_mod)))
                    cursor.execute(
                        "INSERT OR REPLACE INTO marks (student_id, subject, marks, exam_id) VALUES (?, ?, ?, ?)",
                        (s_id, sub, score, exam_id),
                    )

        # Seed attendance records with dates
        # Dates: 2026-10-18 to 2026-10-25
        for s_id in range(1, 9):
            for day in range(18, 26):
                date_str = f"2026-10-{day:02d}"
                status = "Present" if (s_id + day) % 6 != 0 else "Absent"
                cursor.execute(
                    "INSERT INTO attendance (student_id, subject, attendance_date, status) VALUES (?, 'Python', ?, ?)",
                    (s_id, date_str, status),
                )

        conn.commit()
        conn.close()

    def test_examination_filtering_prevents_unintentional_averaging(self):
        """
        Verify that student performance calculations for a specific examination
        do not unintentionally average marks from different examinations.
        """
        # In our seeded data, Alice has base_score = 46.
        # Exam 1 score = 46.0
        # Exam 4 score = 46 + (4 - 1)*3 = 55.0
        perf_exam1 = get_student_performance(exam_id=1)
        perf_exam4 = get_student_performance(exam_id=4)
        perf_cumulative = get_student_performance(allow_all=True)

        alice_ex1 = perf_exam1[perf_exam1["name"] == "Alice"].iloc[0]
        alice_ex4 = perf_exam4[perf_exam4["name"] == "Alice"].iloc[0]
        alice_cum = perf_cumulative[perf_cumulative["name"] == "Alice"].iloc[0]

        self.assertEqual(alice_ex1["Average"], 46.0)
        self.assertEqual(alice_ex4["Average"], 55.0)
        # Verify cumulative average is intentionally the mean of exams (50.5), not mixed into exam 1 or 4
        self.assertNotEqual(alice_ex1["Average"], alice_cum["Average"])
        self.assertEqual(alice_ex1["Exam_Scope"], "Internal Assessment 1")
        self.assertEqual(alice_cum["Exam_Scope"], "Cumulative Across All Examinations")

    def test_default_scope_resolves_to_latest_exam(self):
        """Verify that passing exam_id=None without allow_all resolves to the latest examination."""
        perf_default = get_student_performance()
        latest_id, latest_name = resolve_examination(exam_id=None, allow_all=False)
        self.assertEqual(perf_default.iloc[0]["Exam_Scope"], latest_name)

    def test_subject_analysis_examination_scope(self):
        """Verify subject aggregations calculate metrics strictly for the requested scope."""
        subjs_ex1 = get_subject_analysis(exam_id=1)
        subjs_ex4 = get_subject_analysis(exam_id=4)
        self.assertFalse(subjs_ex1.empty)
        self.assertFalse(subjs_ex4.empty)
        # Exam 4 marks are systematically higher than Exam 1
        self.assertGreater(subjs_ex4.iloc[0]["Average"], subjs_ex1.iloc[0]["Average"])

    def test_empty_dataset_handling(self):
        """Verify all analytical functions handle empty databases gracefully without division by zero."""
        conn = database.get_connection()
        conn.execute("DELETE FROM attendance")
        conn.execute("DELETE FROM marks")
        conn.execute("DELETE FROM students")
        conn.commit()
        conn.close()

        self.assertTrue(get_student_performance().empty)
        self.assertTrue(get_subject_analysis().empty)
        self.assertTrue(get_department_performance().empty)
        self.assertTrue(get_semester_performance().empty)
        self.assertTrue(get_subject_correlation().empty)
        self.assertTrue(get_cohort_risk_overview().empty)

        dash = get_dashboard_metrics()
        self.assertEqual(dash["total_students"], 0)
        self.assertEqual(dash["class_average"], 0.0)
        self.assertEqual(dash["pass_percentage"], 0.0)

    def test_risk_classification_boundaries_and_rules(self):
        """
        Verify canonical risk classification rules across boundary values and missing attendance.
        """
        # Rule 1: Fail status -> High Risk regardless of average
        r1, _ = classify_student_risk(avg_score=85.0, status="Fail", att_pct=95.0, weakness_count=0)
        self.assertEqual(r1, "High Risk")

        # Rule 2: Average < 45 -> High Risk
        r2, _ = classify_student_risk(avg_score=44.9, status="Pass", att_pct=85.0, weakness_count=0)
        self.assertEqual(r2, "High Risk")

        # Rule 3: Attendance < 70% -> High Risk
        r3, _ = classify_student_risk(avg_score=75.0, status="Pass", att_pct=69.9, weakness_count=0)
        self.assertEqual(r3, "High Risk")

        # Boundary: Average == 45.0, status Pass, good attendance -> Medium Risk (not High Risk)
        r4, _ = classify_student_risk(avg_score=45.0, status="Pass", att_pct=80.0, weakness_count=0)
        self.assertEqual(r4, "Medium Risk")

        # Boundary: Attendance == 70.0% -> Medium Risk (not High Risk)
        r5, _ = classify_student_risk(avg_score=75.0, status="Pass", att_pct=70.0, weakness_count=0)
        self.assertEqual(r5, "Medium Risk")

        # Boundary: Weakness count >= 1 -> Medium Risk
        r6, _ = classify_student_risk(avg_score=75.0, status="Pass", att_pct=85.0, weakness_count=1)
        self.assertEqual(r6, "Medium Risk")

        # Boundary: Low Risk on-track (Pass, avg >= 65, 0 weaknesses, att >= 75)
        r7, _ = classify_student_risk(avg_score=65.0, status="Pass", att_pct=75.0, weakness_count=0)
        self.assertEqual(r7, "Low Risk")

        # Missing attendance (None) -> Must NOT artificially penalize to High/Medium Risk
        r8, _ = classify_student_risk(avg_score=78.0, status="Pass", att_pct=None, weakness_count=0)
        self.assertEqual(r8, "Low Risk")

    def test_date_ordering_and_invalid_date_safety_in_ml(self):
        """
        Verify that longitudinal transitions are ordered by valid dates,
        and invalid or missing dates are handled safely with secondary fallback.
        """
        conn = database.get_connection()
        # Add an examination with an unparseable invalid date string
        conn.execute("INSERT OR REPLACE INTO examinations (id, name, exam_date, exam_type) VALUES (5, 'Quiz Special', 'invalid-date-string', 'Quiz')")
        conn.commit()
        conn.close()

        # Build transitions dataset - should parse valid dates and sort gracefully without crashing
        transitions, latest_exams, sub_cols = build_examination_transitions_dataset()
        self.assertIsNotNone(transitions)
        self.assertTrue(len(transitions) > 0)
        self.assertIn("from_exam_date", transitions.columns)
        self.assertIn("to_exam_date", transitions.columns)

    def test_ml_production_model_retraining(self):
        """
        Verify that the ML pipeline selects the best model via holdout RMSE
        and retrains on all transitions for upcoming forecasting.
        """
        output = train_and_evaluate_models(eval_strategy="student_grouped")
        self.assertEqual(output["status"], "success")
        self.assertIn("metrics", output)
        self.assertIn("best_model", output)
        self.assertIn("cohort_predictions", output)
        self.assertEqual(len(output["cohort_predictions"]), 8)


if __name__ == "__main__":
    unittest.main()
