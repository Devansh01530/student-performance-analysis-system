"""
Predictive Analytics and Machine Learning Engine for Academic Performance.
Longitudinal examination-to-examination performance forecasting with zero data leakage:
- Evaluated via Student-Grouped Partitioning (GroupShuffleSplit: no student in test exists in train)
  or Chronological Progression Partitioning (train on earlier examinations, test on later milestones).
- Uses strictly historical attendance records logged prior to the target examination.
- Algorithms: Linear Regression, Decision Tree Regression, Random Forest Regression
- Metric Evaluations: MAE, MSE, RMSE, R-squared
- Upcoming examination forecast for currently enrolled students
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import database


def build_examination_transitions_dataset(target_subject=None):
    """
    Constructs a sequential dataset mapping Exam(t) -> Exam(t+1) performance.
    Guarantees zero data leakage by:
    1. Predicting future examination results strictly from prior examination records.
    2. Calculating attendance strictly from historical logs recorded up to the prior examination date.
    """
    progress = database.get_all_exam_progress()

    if progress.empty or len(progress["exam_id"].unique()) < 2:
        return None, None, []

    # Include exam_date in pivot index
    index_cols = ["student_id", "name", "department", "semester", "exam_id", "exam_name", "exam_date"]
    pivot = progress.pivot_table(
        index=index_cols,
        columns="subject",
        values="marks",
        aggfunc="mean",
    ).reset_index()

    subject_cols = [
        c for c in pivot.columns
        if c not in index_cols
    ]

    pivot["Exam_Average"] = pivot[subject_cols].mean(axis=1).round(2)

    # Pre-fetch and cache historical attendance strictly as of each unique exam date
    unique_exam_dates = pivot["exam_date"].dropna().unique()
    historical_att_by_date = {}
    for ed in unique_exam_dates:
        att_hist = database.get_attendance_summary(before_date=str(ed))
        att_map = {}
        if not att_hist.empty:
            for _, a_row in att_hist.iterrows():
                pct = a_row["attendance_percentage"]
                if pd.notna(pct) and pct is not None:
                    att_map[a_row["student_id"]] = float(pct)
        historical_att_by_date[str(ed)] = att_map

    transitions = []
    latest_exam_per_student = {}

    for s_id, group in pivot.groupby("student_id"):
        sorted_g = group.sort_values("exam_id").reset_index(drop=True)
        latest_exam_per_student[s_id] = sorted_g.iloc[-1]

        for i in range(len(sorted_g) - 1):
            prev_row = sorted_g.iloc[i]
            next_row = sorted_g.iloc[i + 1]

            prev_date = str(prev_row["exam_date"])
            att_map_for_date = historical_att_by_date.get(prev_date, {})
            
            # Historical attendance strictly up to prior examination date
            if s_id in att_map_for_date:
                student_hist_att = att_map_for_date[s_id]
                att_recorded = 1
            else:
                # If unrecorded at that historical timestamp, use recorded historical cohort mean or 75.0 baseline
                cohort_known = list(att_map_for_date.values())
                student_hist_att = float(np.mean(cohort_known)) if cohort_known else 75.0
                att_recorded = 0

            record = {
                "student_id": s_id,
                "name": prev_row["name"],
                "department": prev_row["department"],
                "semester": prev_row["semester"],
                "from_exam_id": prev_row["exam_id"],
                "to_exam_id": next_row["exam_id"],
                "from_exam": prev_row["exam_name"],
                "to_exam": next_row["exam_name"],
                "from_exam_date": prev_date,
                "to_exam_date": str(next_row["exam_date"]),
                "Prev_Average": prev_row["Exam_Average"],
                "Attendance_Pct": round(student_hist_att, 2),
                "Attendance_Recorded": att_recorded,
            }

            for sub in subject_cols:
                record[f"Prev_{sub}"] = prev_row[sub]
                record[f"Next_{sub}"] = next_row[sub]

            record["Next_Average"] = next_row["Exam_Average"]
            transitions.append(record)

    transitions_df = pd.DataFrame(transitions)
    return transitions_df, latest_exam_per_student, subject_cols


def train_and_evaluate_models(target_subject=None, eval_strategy="student_grouped"):
    """
    Trains regression models to predict NEXT examination performance from PREVIOUS examination marks.
    Evaluation Strategies:
    - 'student_grouped': GroupShuffleSplit on student_id. Zero student history leakage: all transition pairs
      for any student in the test set are completely withheld from the training set.
    - 'chronological': Splits by examination timeline. Trains on earlier examinations and tests on the latest milestone.

    Returns:
    - status: 'success' or 'insufficient_data'
    - target: target variable display name
    - eval_strategy_name: display description of the evaluation methodology
    - metrics: DataFrame comparing algorithms (MAE, MSE, RMSE, R2)
    - best_model: name of best performing algorithm
    - test_comparison: actual vs predicted on held-out test transitions
    - cohort_predictions: forecasted scores in the UPCOMING examination for current students
    - transitions_count: total transition pairs
    - train_size: number of training samples
    - test_size: number of testing samples
    - test_students: list of student names in the test holdout
    """
    transitions_df, latest_exams, subject_cols = build_examination_transitions_dataset(target_subject)

    if transitions_df is None or len(transitions_df) < 6:
        return {
            "status": "insufficient_data",
            "message": "Longitudinal prediction requires at least two examination events in the database to train transition models.",
        }

    feature_cols = ["Prev_Average", "Attendance_Pct"] + [f"Prev_{sub}" for sub in subject_cols if f"Prev_{sub}" in transitions_df.columns]

    if target_subject and f"Next_{target_subject}" in transitions_df.columns:
        target_col = f"Next_{target_subject}"
        target_display_name = f"Next Exam: {target_subject}"
    else:
        target_col = "Next_Average"
        target_display_name = "Next Examination Average Score"

    X = transitions_df[feature_cols].copy()
    y = transitions_df[target_col].copy()

    # Apply selected evaluation partition strategy
    if eval_strategy == "chronological" and len(transitions_df["to_exam_id"].unique()) >= 2:
        max_target_exam = transitions_df["to_exam_id"].max()
        train_mask = transitions_df["to_exam_id"] < max_target_exam
        test_mask = transitions_df["to_exam_id"] == max_target_exam

        # Verify both splits have data
        if train_mask.sum() >= 4 and test_mask.sum() >= 2:
            X_train, y_train = X[train_mask], y[train_mask]
            X_test, y_test = X[test_mask], y[test_mask]
            test_indices = transitions_df[test_mask].index
            eval_strategy_name = "Chronological Timeline Split (Trained on Earlier Exams, Evaluated on Latest Exam)"
        else:
            eval_strategy = "student_grouped"

    if eval_strategy == "student_grouped":
        # GroupShuffleSplit by student_id: guarantees zero student leakage between train and test
        groups = transitions_df["student_id"]
        test_fraction = 0.25 if len(transitions_df["student_id"].unique()) >= 8 else 0.33
        gss = GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=42)
        train_idx, test_idx = next(gss.split(X, y, groups=groups))

        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]
        test_indices = transitions_df.iloc[test_idx].index
        eval_strategy_name = "Student-Grouped Holdout (Zero Student Overlap: Test Students Completely Unseen in Training)"

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

    # Test Actual vs Predicted comparison on strictly held-out partition
    test_rows = transitions_df.loc[test_indices]
    best_test_preds = np.clip(predictions_dict[best_model_name], 0.0, 100.0).round(2)

    comparison_df = pd.DataFrame({
        "Student": test_rows["name"].values,
        "From Exam": test_rows["from_exam"].values,
        "Target Exam": test_rows["to_exam"].values,
        "Actual Score": y_test.values.round(2),
        "Predicted Score": best_test_preds,
        "Absolute Error": np.abs(y_test.values - best_test_preds).round(2),
    })

    test_students = sorted(list(test_rows["name"].unique()))

    # Forecast UPCOMING next examination for currently enrolled students
    # Use each student's most recent examination and their up-to-date recorded attendance
    current_att_df = database.get_attendance_summary()
    att_map = {}
    if not current_att_df.empty:
        for _, a_row in current_att_df.iterrows():
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
        "eval_strategy_name": eval_strategy_name,
        "is_small_sample": len(transitions_df) < 30,
        "metrics": metrics_df,
        "best_model": best_model_name,
        "test_comparison": comparison_df,
        "cohort_predictions": cohort_pred_df,
        "transitions_count": len(transitions_df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "test_students": test_students,
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
