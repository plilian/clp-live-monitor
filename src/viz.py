from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd


def fig_price_and_clp(df: pd.DataFrame, stress_thr: float, extreme_thr: float) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time"], y=df["Close"],
        name="Price (Close)", mode="lines", yaxis="y1"
    ))

    fig.add_trace(go.Scatter(
        x=df["time"], y=df["clp"],
        name="CLP (Pressure)", mode="lines", yaxis="y2"
    ))

    fig.add_hline(y=stress_thr, line_dash="dash", annotation_text="Stress", yref="y2")
    fig.add_hline(y=extreme_thr, line_dash="dot", annotation_text="Extreme", yref="y2")

    fig.update_layout(
        title="Price vs CLP (Crowded Leverage Pressure)",
        xaxis_title="Time (UTC)",
        yaxis=dict(title="Price", side="left"),
        yaxis2=dict(title="CLP", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        margin=dict(l=30, r=30, t=60, b=30),
    )
    return fig


def fig_components(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time"], y=df["z_funding"], name="z(Funding)", mode="lines"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["z_oi"], name="z(ΔOI%)", mode="lines"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["z_absret"], name="z(|return|)", mode="lines"))

    fig.update_layout(
        title="Components (Rolling Z-scores)",
        xaxis_title="Time (UTC)",
        yaxis_title="Z-score",
        legend=dict(orientation="h"),
        margin=dict(l=30, r=30, t=60, b=30),
    )
    return fig