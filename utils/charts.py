import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def student_performance_chart(df: pd.DataFrame) -> go.Figure:
    """
    Vertical performance bar chart with modern dark theme and custom color grading.
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = px.bar(
        df,
        x="name",
        y="Average",
        color="Grade",
        title="Student Performance Comparison",
        text="Average",
        color_discrete_map={
            "A+": "#38bdf8",
            "A": "#60a5fa",
            "B": "#818cf8",
            "C": "#a78bfa",
            "D": "#f59e0b",
            "F": "#ef4444",
        },
    )

    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        marker=dict(line=dict(width=1, color="rgba(255,255,255,0.2)")),
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        xaxis_title="Student",
        yaxis_title="Average Marks",
        yaxis_range=[0, 105],
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        margin=dict(l=20, r=20, t=50, b=30),
    )

    return fig


def subject_average_chart(df: pd.DataFrame) -> go.Figure:
    """
    Radar / Polar chart showing subject averages.
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    categories = df["subject"].tolist()
    values = df["Average"].tolist()

    # Close the radar loop
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            name="Subject Average",
            line=dict(color="#38bdf8", width=3),
            fillcolor="rgba(56, 189, 248, 0.25)",
            marker=dict(size=8, color="#ffffff"),
            hovertemplate="Subject: %{theta}<br>Average: %{r:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="Subject Performance Radar",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#94a3b8"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#e2e8f0", size=12),
            ),
            bgcolor="rgba(15, 23, 42, 0.6)",
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
    )

    return fig


def grade_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart of grade distributions with high-contrast color scheme.
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    grade_counts = df["Grade"].value_counts().reset_index()
    grade_counts.columns = ["Grade", "Students"]

    color_map = {
        "A+": "#38bdf8",
        "A": "#60a5fa",
        "B": "#818cf8",
        "C": "#a78bfa",
        "D": "#f59e0b",
        "F": "#ef4444",
    }

    colors = [color_map.get(g, "#64748b") for g in grade_counts["Grade"]]

    fig = px.pie(
        grade_counts,
        names="Grade",
        values="Students",
        title="Grade Distribution",
        hole=0.55,
        color="Grade",
        color_discrete_map=color_map,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#0f172a", width=2)),
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        margin=dict(l=20, r=20, t=50, b=30),
    )

    return fig


def pass_fail_chart(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart of Pass vs Fail distribution.
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    status_counts = df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Students"]

    color_map = {"Pass": "#10b981", "Fail": "#ef4444"}

    fig = px.pie(
        status_counts,
        names="Status",
        values="Students",
        title="Pass vs Fail Distribution",
        hole=0.55,
        color="Status",
        color_discrete_map=color_map,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#0f172a", width=2)),
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        margin=dict(l=20, r=20, t=50, b=30),
    )

    return fig
