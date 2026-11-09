"""
Predictive Analytics and Machine Learning Engine for Academic Performance.
Longitudinal examination-to-examination performance forecasting with zero data leakage:
- Uses historical examination marks (Internal 1, Internal 2, Mid-Term) to predict subsequent examination performance
- Algorithms: Linear Regression, Decision Tree Regression, Random Forest Regression
- Independent holdout Train-Test splitting
- Metric Evaluations: MAE, MSE, RMSE, R-squared
- Upcoming examination forecast for currently enrolled students
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import database


def build_examination_transitions_dataset(target_subject=None):
    """
    Constructs a sequential dataset mapping Exam(t) -> Exam(t+1) performance.
    Guarantees ZERO data leakage by predicting future examination results
    strictly from prior examination records and attendance.
    """
    progress = database.get_all_exam_progress()
    att_df = database.get_attendance_summary()

    if progress.empty or len(progress["exam_id"].unique()) < 2:
        return None, None, []

    # Pivot to get wide marks per student per examination
    pivot = progress.pivot_table(
        index=["student_id", "name", "department", "semester", "exam_id", "exam_name"],
        columns="subject",
        values="marks",
        aggfunc="mean",
    ).reset_index()

    subject_cols = [
        c for c in pivot.columns
        if c not in ["student_id", "name", "department", "semester", "exam_id", "exam_name"]
    ]

    pivot["Exam_Average"] = pivot[subject_cols].mean(axis=1).round(2)

    # Attendance mapping
    att_dict = {}
    if not att_df.empty:
        for _, a_row in att_df.iterrows():
            pct = a_row["attendance_percentage"]
            if pd.notna(pct) and pct is not None:
                att_dict[a_row["student_id"]] = float(pct)

    # Mean recorded attendance fallback (or 75.0 if completely unrecorded)
    valid_att_vals = list(att_dict.values())
    default_att = float(np.mean(valid_att_vals)) if valid_att_vals else 75.0

    transitions = []
    latest_exam_per_student = {}

    for s_id, group in pivot.groupby("student_id"):
        sorted_g = group.sort_values("exam_id").reset_index(drop=True)
        latest_exam_per_student[s_id] = sorted_g.iloc[-1]

        student_att = att_dict.get(s_id, default_att)

        for i in range(len(sorted_g) - 1):
            prev_row = sorted_g.iloc[i]
            next_row = sorted_g.iloc[i + 1]

            record = {
                "student_id": s_id,
                "name": prev_row["name"],
                "department": prev_row["department"],
                "semester": prev_row["semester"],
                "from_exam": prev_row["exam_name"],
                "to_exam": next_row["exam_name"],
                "Prev_Average": prev_row["Exam_Average"],
                "Attendance_Pct": student_att,
            }

            for sub in subject_cols:
                record[f"Prev_{sub}"] = prev_row[sub]
                record[f"Next_{sub}"] = next_row[sub]

            record["Next_Average"] = next_row["Exam_Average"]
            transitions.append(record)

    transitions_df = pd.DataFrame(transitions)
    return transitions_df, latest_exam_per_student, subject_cols


def train_and_evaluate_models(target_subject=None):
    """
    Trains regression models to predict NEXT examination performance from PREVIOUS examination marks.
    Returns:
    - status: 'success' or 'insufficient_data'
    - target: target variable name
    - metrics: DataFrame comparing algorithms (MAE, MSE, RMSE, R2)
    - best_model: name of best performing algorithm
    - test_comparison: actual vs predicted on held-out test transitions
    - cohort_predictions: forecasted scores in the UPCOMING examination for current students
    - transitions_count: number of transition pairs used in training
    """
    transitions_df, latest_exams, subject_cols = build_examination_transitions_dataset(target_subject)

    if transitions_df is None or len(transitions_df) < 6:
        return {
            "status": "insufficient_data",
            "message": "Longitudinal prediction requires at least two examination events in the database to train transition models.",
        }

    # Features: Prior Exam Average, Prior Course Marks, and Attendance Rate
    feature_cols = ["Prev_Average", "Attendance_Pct"] + [f"Prev_{sub}" for sub in subject_cols if f"Prev_{sub}" in transitions_df.columns]

    # Target: Next Exam Average or Next Exam Target Subject
    if target_subject and f"Next_{target_subject}" in transitions_df.columns:
        target_col = f"Next_{target_subject}"
        target_display_name = f"Next Exam: {target_subject}"
    else:
        target_col = "Next_Average"
        target_display_name = "Next Examination Average Score"

    X = transitions_df[feature_cols].copy()
    y = transitions_df[target_col].copy()

    # Train-test split (25% holdout)
    test_size = 0.25 if len(transitions_df) >= 12 else 0.33
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree Regression": DecisionTreeRegressor(random_state=42, max_depth=3),
        "Random Forest Regression": RandomForestRegressor(n_estimators=50, random_state=42, max_depth=3),
    }

    metrics_list = []
    predictions_dict = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        predictions_dict[name] = y_pred

        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)

        metrics_list.append({
            "Algorithm": name,
            "MAE": round(float(mae), 3),
            "MSE": round(float(mse), 3),
            "RMSE": round(float(rmse), 3),
            "R2_Score": round(float(r2), 3),
        })

    metrics_df = pd.DataFrame(metrics_list)
    best_model_name = metrics_df.sort_values(by="RMSE").iloc[0]["Algorithm"]
    best_model = models[best_model_name]

    # Test Actual vs Predicted comparison
    test_rows = transitions_df.loc[X_test.index]
    best_test_preds = np.clip(predictions_dict[best_model_name], 0.0, 100.0).round(2)

    comparison_df = pd.DataFrame({
        "Student": test_rows["name"].values,
        "From Exam": test_rows["from_exam"].values,
        "Target Exam": test_rows["to_exam"].values,
        "Actual Score": y_test.values.round(2),
        "Predicted Score": best_test_preds,
        "Absolute Error": np.abs(y_test.values - best_test_preds).round(2),
    })

    # Forecast UPCOMING next examination for currently enrolled students
    # Use each student's most recent examination as input features
    att_df = database.get_attendance_summary()
    att_map = {}
    if not att_df.empty:
        for _, a_row in att_df.iterrows():
            pct = a_row["attendance_percentage"]
            if pd.notna(pct) and pct is not None:
                att_map[a_row["student_id"]] = float(pct)

    cohort_forecasts = []
    for s_id, latest_row in latest_exams.items():
        s_att = att_map.get(s_id, transitions_df["Attendance_Pct"].mean())

        x_curr = {"Prev_Average": latest_row["Exam_Average"], "Attendance_Pct": s_att}
        for sub in subject_cols:
            x_curr[f"Prev_{sub}"] = latest_row[sub]

        x_curr_df = pd.DataFrame([x_curr])[feature_cols]
        predicted_score = float(np.clip(best_model.predict(x_curr_df)[0], 0.0, 100.0).round(2))

        curr_avg = float(latest_row["Exam_Average"])
        delta = round(predicted_score - curr_avg, 2)

        if predicted_score >= 90:
            grade = "A+"
        elif predicted_score >= 80:
            grade = "A"
        elif predicted_score >= 70:
            grade = "B"
        elif predicted_score >= 60:
            grade = "C"
        elif predicted_score >= 50:
            grade = "D"
        else:
            grade = "F"

        risk = "High Risk" if predicted_score < 45.0 else "Medium Risk" if predicted_score < 65.0 else "Low Risk"

        cohort_forecasts.append({
            "id": s_id,
            "Student": latest_row["name"],
            "Latest Exam": latest_row["exam_name"],
            "Latest Score": curr_avg,
            "Forecasted Score": predicted_score,
            "Expected Delta": delta,
            "Forecasted Grade": grade,
            "Predicted Risk": risk,
        })

    cohort_pred_df = pd.DataFrame(cohort_forecasts).sort_values("Forecasted Score", ascending=False)

    return {
        "status": "success",
        "target": target_display_name,
        "is_small_sample": len(transitions_df) < 30,
        "metrics": metrics_df,
        "best_model": best_model_name,
        "test_comparison": comparison_df,
        "cohort_predictions": cohort_pred_df,
        "transitions_count": len(transitions_df),
    }


def simulate_student_whatif(current_average, study_hours_delta=0.0, attendance_rate=85.0):
    """
    Simulates projected next examination score under altered study habits and attendance rate.
    Uses non-linear marginal returns with asymptotic saturation.
    """
    study_boost = (study_hours_delta * 1.35) * (1.0 - (current_average / 112.0))
    att_adj = ((attendance_rate - 75.0) / 25.0) * 2.5
    forecast = max(0.0, min(100.0, round(current_average + study_boost + att_adj, 2)))
    diff = round(forecast - current_average, 2)
    return forecast, diff
