import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database
from utils.predict import train_and_evaluate_models, simulate_student_whatif
from utils.analysis import get_student_performance
from utils.style import apply_custom_css, add_sidebar_branding

st.set_page_config(
    page_title="Predictive Analytics",
    layout="wide",
)
apply_custom_css()
add_sidebar_branding()

st.title("Predictive Analytics and Machine Learning")
st.write(
    "Supervised machine learning algorithms trained on student academic records to forecast performance, evaluate regression metrics, and model intervention scenarios."
)

st.divider()

perf = get_student_performance()

if perf.empty:
    st.info("No student records available for machine learning training.")
else:
    # Model Configuration
    st.subheader("Model Configuration & Training Parameters")

    subject_cols = [
        c for c in perf.columns
        if c not in ["id", "name", "department", "semester", "Average", "Total", "Grade", "Status", "Rank"]
    ]

    target_choice = st.selectbox(
        "Prediction Target Variable",
        ["Overall Academic Average"] + [f"Subject: {s}" for s in subject_cols],
    )

    target_subject = None
    if target_choice.startswith("Subject: "):
        target_subject = target_choice.replace("Subject: ", "")

    # Train Models
    ml_output = train_and_evaluate_models(target_subject=target_subject)

    if ml_output.get("status") == "insufficient_data":
        st.warning(ml_output["message"])
    else:
        st.markdown(
            """
            <div class="card-3d" style="border-left: 4px solid #38bdf8; margin-bottom: 20px;">
                <div style="font-size: 0.8rem; text-transform: uppercase; color: #38bdf8; font-weight: 700;">
                    Zero Data Leakage Architecture
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: #ffffff; margin-top: 4px;">
                    Longitudinal Examination-to-Examination Forecasting
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 6px; line-height: 1.6;">
                    Unlike naive models that predict an average using the same subject marks that comprise it, this predictive engine trains
                    strictly on historical transitions from prior examinations (Internal 1, Internal 2, Mid-Term) to forecast performance in subsequent examinations.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ml_output["is_small_sample"]:
            st.info(
                f"Sample Size Notice: Trained on {ml_output['transitions_count']} historical examination transition pairs. "
                "Regression metrics are computed across holdout test splits. "
                "Predictions represent estimated academic trends rather than guaranteed future marks."
            )

        # Model Comparison Table
        st.subheader("Algorithm Evaluation & Comparison")
        st.write("Models evaluated using independent test holdouts across Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and R-squared.")

        metrics_df = ml_output["metrics"]
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        st.caption(f"Top performing algorithm by minimum RMSE: **{ml_output['best_model']}**")

        st.divider()

        # Comparison Chart of Models
        st.subheader("Regression Error Metrics Comparison")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_err = px.bar(
                metrics_df,
                x="Algorithm",
                y="RMSE",
                color="Algorithm",
                text="RMSE",
                title="Root Mean Squared Error (Lower is Better)",
                color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399"],
            )
            fig_err.update_traces(texttemplate="%{text:.3f}", textposition="outside")
            fig_err.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                showlegend=False,
            )
            st.plotly_chart(fig_err, use_container_width=True)

        with col_m2:
            fig_r2 = px.bar(
                metrics_df,
                x="Algorithm",
                y="R2_Score",
                color="Algorithm",
                text="R2_Score",
                title="R-Squared Goodness of Fit (Closer to 1.0 is Better)",
                color_discrete_sequence=["#34d399", "#38bdf8", "#818cf8"],
            )
            fig_r2.update_traces(texttemplate="%{text:.3f}", textposition="outside")
            fig_r2.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                showlegend=False,
            )
            st.plotly_chart(fig_r2, use_container_width=True)

        st.divider()

        # Actual vs Predicted Test Comparison
        st.subheader("Actual versus Predicted Marks (Holdout Test Set)")
        test_comp = ml_output["test_comparison"]

        col_tc1, col_tc2 = st.columns([1, 1])
        with col_tc1:
            st.dataframe(test_comp, use_container_width=True, hide_index=True)

        with col_tc2:
            fig_act_pred = px.scatter(
                test_comp,
                x="Actual Score",
                y="Predicted Score",
                text="Student",
                title="Actual vs Predicted Marks Scatter",
                color="Absolute Error",
                color_continuous_scale="Viridis",
            )
            # Add identity 45-degree line
            fig_act_pred.add_trace(
                go.Scatter(
                    x=[0, 100],
                    y=[0, 100],
                    mode="lines",
                    name="Ideal (1:1)",
                    line=dict(color="#f43f5e", dash="dash"),
                )
            )
            fig_act_pred.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.6)",
                xaxis_range=[0, 105],
                yaxis_range=[0, 105],
            )
            st.plotly_chart(fig_act_pred, use_container_width=True)

        st.divider()

        # Full Cohort Forecast Registry
        st.subheader("Full Cohort Projected Performance Registry")
        cohort_pred = ml_output["cohort_predictions"]
        st.dataframe(cohort_pred, use_container_width=True, hide_index=True)

        st.divider()

        # 3D Trajectory Surface
        st.subheader("3D Forecast Coordinate Projection")
        st.write("Interactive 3D view: Latest Exam Score (X) by Forecasted Score (Y) by Net Expected Differential (Z).")

        fig_3d_pred = go.Figure(
            data=[
                go.Scatter3d(
                    x=cohort_pred["Latest Score"],
                    y=cohort_pred["Forecasted Score"],
                    z=cohort_pred["Expected Delta"],
                    mode="markers+text",
                    text=cohort_pred["Student"],
                    textposition="top center",
                    textfont=dict(size=10, color="#e2e8f0"),
                    marker=dict(
                        size=10,
                        color=cohort_pred["Forecasted Score"],
                        colorscale="Viridis",
                        colorbar=dict(title=dict(text="Score", font=dict(color="#e2e8f0"))),
                        opacity=0.9,
                        line=dict(color="#ffffff", width=1),
                    ),
                    hovertemplate=(
                        "Student: %{text}<br>"
                        "Latest Score: %{x:.2f}<br>"
                        "Forecasted: %{y:.2f}<br>"
                        "Net Delta: %{z:+.2f}<br>"
                        "<extra></extra>"
                    ),
                )
            ]
        )
        fig_3d_pred.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, b=0, t=30),
            scene=dict(
                xaxis=dict(title="Latest Score", backgroundcolor="rgba(15, 23, 42, 0.6)", showbackground=True),
                yaxis=dict(title="Forecasted Score", backgroundcolor="rgba(15, 23, 42, 0.6)", showbackground=True),
                zaxis=dict(title="Expected Delta", backgroundcolor="rgba(15, 23, 42, 0.6)", showbackground=True),
                camera=dict(eye=dict(x=1.6, y=1.5, z=1.2)),
            ),
        )
        st.plotly_chart(fig_3d_pred, use_container_width=True)

        st.divider()

        # Interactive What-If Simulator
        st.subheader("What-If Academic Intervention Simulator")
        st.write("Simulate expected score trajectory for an individual student under altered study habits and attendance rates.")

        students = database.get_students()
        sel_s_id = st.selectbox(
            "Select Student for Simulation",
            students["id"].tolist(),
            format_func=lambda x: f"{students.loc[students['id'] == x, 'name'].iloc[0]} (ID: {x})",
        )

        s_current_avg = float(perf[perf["id"] == sel_s_id].iloc[0]["Average"])

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            sim_hours = st.slider("Additional Study Hours / Week", -5.0, 15.0, 3.0, step=0.5)
        with col_w2:
            sim_att = st.slider("Target Attendance Rate (%)", 50.0, 100.0, 90.0, step=1.0)

        sim_forecast, sim_delta = simulate_student_whatif(s_current_avg, sim_hours, sim_att)

        sw1, sw2, sw3 = st.columns(3)
        sw1.metric("Current Average", f"{s_current_avg:.2f}")
        sw2.metric("Simulated Forecast", f"{sim_forecast:.2f}", delta=f"{sim_delta:+.2f}")
        sw3.metric("Projected Grade", "A+" if sim_forecast >= 90 else "A" if sim_forecast >= 80 else "B" if sim_forecast >= 70 else "C" if sim_forecast >= 60 else "D" if sim_forecast >= 50 else "F")
