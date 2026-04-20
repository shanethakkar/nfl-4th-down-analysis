"""
Coach Comparison — NFL 4th Down Decision Analysis
Season-by-season DQS and go-for-it rate for up to 5 coaches.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Coach Comparison · NFL 4th Down Analysis",
    page_icon="🏈",
    layout="wide",
)


ROOT = Path(__file__).resolve().parent.parent.parent

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_season_stats():
    return pd.read_csv(ROOT / "outputs" / "coach_season_stats.csv")

@st.cache_data
def load_grades():
    return pd.read_csv(ROOT / "outputs" / "coach_grades.csv")

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_COACHES = ["Dan Campbell", "Andy Reid", "Kyle Shanahan",
                   "Bill Belichick", "Mike McCarthy"]

# 10-color qualitative palette (professional, accessible)
PALETTE = [
    "#C5203B",  # red        → Campbell default
    "#E65100",  # orange
    "#1565C0",  # blue
    "#4A148C",  # purple
    "#546E7A",  # steel blue
    "#2E7D32",  # green
    "#00838F",  # teal
    "#6D4C41",  # brown
    "#F57F17",  # amber
    "#37474F",  # dark grey
]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏈 NFL Coach 4th Down Comparison")
st.markdown(
    "Compare up to **5 coaches** head-to-head on 4th down decision quality and aggressiveness "
    "across their full careers. Select any coaches from the dropdown below."
)

season_stats = load_season_stats()
grades       = load_grades()

all_coaches  = sorted(season_stats["coach_name"].unique().tolist())

# ── Coach selector ────────────────────────────────────────────────────────────
defaults = [c for c in DEFAULT_COACHES if c in all_coaches]
selected = st.multiselect(
    "Select coaches to compare (up to 5)",
    options=all_coaches,
    default=defaults,
    max_selections=5,
)

if not selected:
    st.info("Select at least one coach above to see the comparison.")
    st.stop()

# Assign colors
coach_colors = {coach: PALETTE[i % len(PALETTE)] for i, coach in enumerate(selected)}

# ── Filter data ───────────────────────────────────────────────────────────────
stats = season_stats[season_stats["coach_name"].isin(selected)].copy()
grade_rows = grades[grades["coach_name"].isin(selected)].copy()

# ── Summary cards ─────────────────────────────────────────────────────────────
st.subheader("Career Summary")

cols = st.columns(len(selected))
for i, coach in enumerate(selected):
    color = coach_colors[coach]
    gr = grade_rows[grade_rows["coach_name"] == coach]
    if gr.empty:
        cols[i].warning(f"{coach}\nNo career data")
        continue
    g = gr.iloc[0]
    cols[i].markdown(
        f"""
        <div style="
            border-top:4px solid {color};
            background:#FAFAFA;
            border-radius:6px;
            padding:14px 16px;
        ">
            <b style="color:{color}; font-size:1.05em">{coach}</b><br>
            <span style="color:#546E7A; font-size:0.88em">{g['seasons']}</span><br><br>
            <b>DQS:</b> {g['dqs']:.4f} <span style="color:#78909C;font-size:0.85em">(rank #{int(g['dqs_rank'])})</span><br>
            <b>ODR:</b> {g['odr']*100:.1f}%<br>
            <b>Go rate:</b> {g['go_rate']*100:.1f}%<br>
            <b>Decisions:</b> {int(g['total_decisions']):,}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

# ── Left: DQS by season ───────────────────────────────────────────────────────
with chart_col1:
    st.subheader("Decision Quality (DQS) by Season")
    st.caption("Lower DQS = better decisions. Closer to zero means fewer WPA points left on the table.")

    fig_dqs = go.Figure()

    # League average reference line
    league_dqs = (
        season_stats
        .groupby("season")["dqs"]
        .mean()
        .reset_index()
    )
    fig_dqs.add_trace(go.Scatter(
        x=league_dqs["season"],
        y=league_dqs["dqs"],
        mode="lines",
        name="League avg",
        line=dict(color="#CFD8DC", width=1.5, dash="dot"),
        hovertemplate="League avg %{x}: %{y:.4f}<extra></extra>",
    ))

    for coach in selected:
        sub = stats[stats["coach_name"] == coach].sort_values("season")
        if sub.empty:
            continue
        fig_dqs.add_trace(go.Scatter(
            x=sub["season"],
            y=sub["dqs"],
            mode="lines+markers",
            name=coach,
            line=dict(color=coach_colors[coach], width=2.5),
            marker=dict(size=7, color=coach_colors[coach]),
            customdata=sub[["n_decisions", "odr"]].values,
            hovertemplate=(
                f"<b>{coach}</b> %{{x}}<br>"
                "DQS: %{y:.4f}<br>"
                "Decisions: %{customdata[0]}<br>"
                "ODR: %{customdata[1]:.1%}<extra></extra>"
            ),
        ))

    fig_dqs.update_layout(
        height=380,
        yaxis=dict(title="DQS (lower = better)", autorange="reversed",
                   tickformat=".4f"),
        xaxis=dict(title="Season", dtick=2),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=60, r=20, t=40, b=50),
    )
    st.plotly_chart(fig_dqs, use_container_width=True)

# ── Right: Go-for-it rate by season ──────────────────────────────────────────
with chart_col2:
    st.subheader("Go-For-It Rate by Season")
    st.caption("How often each coach chose to go for it on 4th down (vs punt or kick a field goal).")

    fig_go = go.Figure()

    # League average reference line
    league_go = (
        season_stats
        .groupby("season")["go_rate"]
        .mean()
        .reset_index()
    )
    fig_go.add_trace(go.Scatter(
        x=league_go["season"],
        y=league_go["go_rate"],
        mode="lines",
        name="League avg",
        line=dict(color="#CFD8DC", width=1.5, dash="dot"),
        hovertemplate="League avg %{x}: %{y:.1%}<extra></extra>",
    ))

    for coach in selected:
        sub = stats[stats["coach_name"] == coach].sort_values("season")
        if sub.empty:
            continue
        fig_go.add_trace(go.Scatter(
            x=sub["season"],
            y=sub["go_rate"],
            mode="lines+markers",
            name=coach,
            line=dict(color=coach_colors[coach], width=2.5),
            marker=dict(size=7, color=coach_colors[coach]),
            customdata=sub[["n_decisions"]].values,
            hovertemplate=(
                f"<b>{coach}</b> %{{x}}<br>"
                "Go rate: %{y:.1%}<br>"
                "Decisions: %{customdata[0]}<extra></extra>"
            ),
        ))

    fig_go.update_layout(
        height=380,
        yaxis=dict(title="Go-For-It Rate", tickformat=".0%"),
        xaxis=dict(title="Season", dtick=2),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=60, r=20, t=40, b=50),
    )
    st.plotly_chart(fig_go, use_container_width=True)

# ── Season-by-season table ────────────────────────────────────────────────────
st.divider()
st.subheader("Season-by-Season Detail")

coach_tab = st.selectbox("View season breakdown for:", selected)
detail = (
    stats[stats["coach_name"] == coach_tab]
    .sort_values("season", ascending=False)
    [["season", "n_decisions", "go_rate", "dqs", "odr", "punt_rate", "fg_rate"]]
    .copy()
)
detail["go_rate"]   = (detail["go_rate"]   * 100).round(1).astype(str) + "%"
detail["odr"]       = (detail["odr"]       * 100).round(1).astype(str) + "%"
detail["punt_rate"] = (detail["punt_rate"] * 100).round(1).astype(str) + "%"
detail["fg_rate"]   = (detail["fg_rate"]   * 100).round(1).astype(str) + "%"
detail["dqs"]       = detail["dqs"].round(5)
detail.columns = ["Season", "Decisions", "Go Rate", "DQS",
                  "ODR", "Punt Rate", "FG Rate"]
st.dataframe(detail, use_container_width=True, hide_index=True)

st.caption(
    "**DQS** = mean WPA gap between optimal and actual decision (lower = better). "
    "**ODR** = % of plays where optimal decision was made. "
    "Minimum 20 decisions per season to appear. "
    "Data: nflfastR, 1999–2025."
)
