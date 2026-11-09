import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np


def student_performance_3d(performance: pd.DataFrame) -> go.Figure:
    """
    Renders an interactive 3D scatter chart of student performance.
    X: Semester
    Y: Average Marks
    Z: Total Marks
    Size: Inverted Rank (Rank 1 has the largest marker)
    Color: Grade
    Zero icons, high-depth visual aesthetics.
    """
    if performance.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="No student records available for 3D projection.",
                    showarrow=False,
                    font=dict(color="#94a3b8", size=14),
                )
            ],
        )
        return fig

    df = performance.copy()
    # Invert rank for size so rank 1 is largest
    max_rank = df["Rank"].max() if "Rank" in df.columns else 10
    df["marker_size"] = df["Rank"].apply(lambda r: max(10, (max_rank - r + 3) * 3))

    color_map = {
        "A+": "#38bdf8",
        "A": "#60a5fa",
        "B": "#818cf8",
        "C": "#a78bfa",
        "D": "#f59e0b",
        "F": "#ef4444",
    }

    fig = go.Figure()

    for grade in df["Grade"].unique():
        sub = df[df["Grade"] == grade]
        color = color_map.get(grade, "#38bdf8")

        fig.add_trace(
            go.Scatter3d(
                x=sub["semester"],
                y=sub["Average"],
                z=sub["Total"],
                mode="markers+text",
                name=f"Grade {grade}",
                text=sub["name"],
                textposition="top center",
                textfont=dict(size=10, color="#e2e8f0"),
                marker=dict(
                    size=sub["marker_size"],
                    color=color,
                    opacity=0.88,
                    line=dict(color="#ffffff", width=1.5),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Semester: %{x}<br>"
                    "Average: %{y:.2f}<br>"
                    "Total Marks: %{z}<br>"
                    f"Grade: {grade}<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, b=0, t=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1"),
        ),
        scene=dict(
            xaxis=dict(
                title="Semester",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
                zerolinecolor="rgba(255, 255, 255, 0.2)",
            ),
            yaxis=dict(
                title="Average Marks",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
                zerolinecolor="rgba(255, 255, 255, 0.2)",
            ),
            zaxis=dict(
                title="Total Marks",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
                zerolinecolor="rgba(255, 255, 255, 0.2)",
            ),
            camera=dict(
                eye=dict(x=1.6, y=1.5, z=1.2),
            ),
        ),
    )
    return fig


def subject_landscape_3d(subject_data: pd.DataFrame) -> go.Figure:
    """
    Renders a 3D bar / surface representation of subject metrics.
    Comparing Average, Highest, and Lowest across all subjects in 3D depth space.
    """
    if subject_data.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    subjects = subject_data["subject"].tolist()
    metrics = ["Lowest", "Average", "Highest"]
    colors = ["#f43f5e", "#38bdf8", "#10b981"]

    fig = go.Figure()

    for idx, metric in enumerate(metrics):
        if metric in subject_data.columns:
            values = subject_data[metric].tolist()
            fig.add_trace(
                go.Scatter3d(
                    x=subjects,
                    y=[metric] * len(subjects),
                    z=values,
                    mode="lines+markers",
                    name=metric,
                    line=dict(color=colors[idx], width=6),
                    marker=dict(
                        size=8,
                        color=colors[idx],
                        symbol="circle",
                        line=dict(color="#ffffff", width=1),
                    ),
                    hovertemplate=(
                        "Subject: %{x}<br>"
                        "Metric: %{y}<br>"
                        "Score: %{z:.2f}<br>"
                        "<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, b=0, t=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1"),
        ),
        scene=dict(
            xaxis=dict(
                title="Subject",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            yaxis=dict(
                title="Dimension",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            zaxis=dict(
                title="Score",
                range=[0, 100],
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            camera=dict(
                eye=dict(x=1.7, y=-1.5, z=1.3),
            ),
        ),
    )
    return fig


def student_marks_surface_3d(marks_data: pd.DataFrame) -> go.Figure:
    """
    Renders 3D coordinate space mapping Students (X) x Subjects (Y) x Marks (Z).
    Provides deep visibility into multi-dimensional grade distributions.
    """
    if marks_data.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=marks_data["name"],
                y=marks_data["subject"],
                z=marks_data["marks"],
                mode="markers",
                marker=dict(
                    size=10,
                    color=marks_data["marks"],
                    colorscale="Viridis",
                    colorbar=dict(
                        title=dict(text="Marks", font=dict(color="#e2e8f0")),
                        tickfont=dict(color="#e2e8f0"),
                    ),
                    opacity=0.9,
                    line=dict(color="#ffffff", width=1),
                ),
                hovertemplate=(
                    "Student: %{x}<br>"
                    "Subject: %{y}<br>"
                    "Marks: %{z}<br>"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, b=0, t=30),
        scene=dict(
            xaxis=dict(
                title="Student",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            yaxis=dict(
                title="Subject",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            zaxis=dict(
                title="Marks",
                range=[0, 100],
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="rgba(255, 255, 255, 0.1)",
                showbackground=True,
            ),
            camera=dict(
                eye=dict(x=1.6, y=1.6, z=1.2),
            ),
        ),
    )
    return fig
