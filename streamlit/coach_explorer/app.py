"""
Coach Explorer — NFL 4th Down Decision Analysis
Interactive scatter plot of all 167 qualifying coaches: aggression vs decision quality.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NFL Coach Explorer · 4th Down Analysis",
    page_icon="🏈",
    layout="wide",
)


ROOT = Path(__file__).resolve().parent.parent.parent

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(ROOT / "outputs" / "coach_grades.csv")
    # Parse season range from "YYYY–YYYY" string
    split = df["seasons"].str.split("–", expand=True)
    df["season_start"] = split[0].astype(int)
    df["season_end"]   = split[1].astype(int)
    return df

def assign_archetypes(df):
    """Compute archetypes relative to the filtered set's medians."""
    df = df.copy()
    med_go  = df["go_rate"].median()
    med_dqs = df["dqs"].median()
    def arch(row):
        agg = row["go_rate"] >= med_go
        acc = row["dqs"]     <= med_dqs
        if   agg and     acc: return "Aggressive + Accurate"
        if   agg and not acc: return "Aggressive + Inaccurate"
        if not agg and   acc: return "Conservative + Accurate"
        return "Conservative + Inaccurate"
    df["archetype"] = df.apply(arch, axis=1)
    df["_med_go"]   = med_go
    df["_med_dqs"]  = med_dqs
    return df

# ── Constants ─────────────────────────────────────────────────────────────────
ARCH_COLORS = {
    "Aggressive + Accurate":    "#2E7D32",
    "Aggressive + Inaccurate":  "#E65100",
    "Conservative + Accurate":  "#1565C0",
    "Conservative + Inaccurate":"#78909C",
}
ARCH_DESC = {
    "Aggressive + Accurate":    "Goes for it often AND makes the right call — the ideal coach",
    "Aggressive + Inaccurate":  "Goes for it often but makes suboptimal choices",
    "Conservative + Accurate":  "Punts frequently but makes the right call when they do decide",
    "Conservative + Inaccurate":"Punts too much AND makes suboptimal calls — worst of both",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

all_coaches = load_data()

# Compute fixed axis ranges from the full dataset (all coaches, min 50 decisions)
# so the viewport never shifts when filters change.
_all_qual = all_coaches[all_coaches["total_decisions"] >= 50]
X_MIN = _all_qual["go_rate"].min() * 0.97
X_MAX = _all_qual["go_rate"].max() * 1.03
Y_MIN = _all_qual["dqs"].min() * 0.97   # lower DQS = better, so this is "top" of chart
Y_MAX = _all_qual["dqs"].max() * 1.03

min_decisions = st.sidebar.slider(
    "Minimum career decisions", min_value=50, max_value=500, value=100, step=50
)
season_range = st.sidebar.slider(
    "Season range", min_value=1999, max_value=2025, value=(1999, 2025), step=1
)
highlight_input = st.sidebar.text_input(
    "🔍 Highlight a coach", placeholder="e.g. Dan Campbell"
)

# ── Filter ────────────────────────────────────────────────────────────────────
df = all_coaches[all_coaches["total_decisions"] >= min_decisions].copy()

# Keep coaches whose tenure overlaps with the selected season range
df = df[
    (df["season_start"] <= season_range[1]) &
    (df["season_end"]   >= season_range[0])
]

df = assign_archetypes(df)
med_go  = df["_med_go"].iloc[0]  if len(df) > 0 else 0.14
med_dqs = df["_med_dqs"].iloc[0] if len(df) > 0 else 0.0086

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏈 NFL Coach Explorer: Aggression vs Decision Quality")
st.markdown(
    "Every qualifying NFL head coach (1999–2025) plotted by **how often they go for it** "
    "and **how good their 4th down decisions are**. Lower DQS = better decisions. "
    "Median lines divide coaches into four archetypes."
)

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Coaches shown", len(df))
col_b.metric("Median go-for-it rate", f"{med_go*100:.1f}%")
col_c.metric("Median DQS", f"{med_dqs:.4f}")
col_d.metric("Seasons covered", f"{season_range[0]}–{season_range[1]}")

st.divider()

# ── Build chart ───────────────────────────────────────────────────────────────
fig = go.Figure()

# One trace per archetype for clean legend
for arch, color in ARCH_COLORS.items():
    sub = df[df["archetype"] == arch]
    if sub.empty:
        continue
    fig.add_trace(go.Scatter(
        x=sub["go_rate"],
        y=sub["dqs"],
        mode="markers",
        name=arch,
        marker=dict(color=color, size=8, opacity=0.75,
                    line=dict(color="white", width=0.5)),
        customdata=sub[["coach_name", "seasons", "total_decisions",
                         "odr", "dqs_rank"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Seasons: %{customdata[1]}<br>"
            "Go-for-it: %{x:.1%}<br>"
            "DQS: %{y:.4f}<br>"
            "ODR: %{customdata[3]:.1%}<br>"
            "Decisions: %{customdata[2]:,}<br>"
            "DQS Rank: #%{customdata[4]}<extra></extra>"
        ),
    ))

# Highlight specific coach
if highlight_input:
    match = df[df["coach_name"].str.contains(highlight_input, case=False, na=False)]
    if not match.empty:
        fig.add_trace(go.Scatter(
            x=match["go_rate"],
            y=match["dqs"],
            mode="markers+text",
            name=f"★ {highlight_input}",
            marker=dict(color="#C5203B", size=14, symbol="star",
                        line=dict(color="white", width=1)),
            text=match["coach_name"],
            textposition="top center",
            textfont=dict(size=11, color="#C5203B"),
        ))
    else:
        st.sidebar.warning(f"No match for '{highlight_input}'")

# Median reference lines
fig.add_hline(
    y=med_dqs, line_dash="dash", line_color="#B0BEC5", line_width=1.2,
    annotation_text=f"Median DQS ({med_dqs:.4f})",
    annotation_position="right", annotation_font_size=10,
)
fig.add_vline(
    x=med_go, line_dash="dash", line_color="#B0BEC5", line_width=1.2,
    annotation_text=f"Median go rate ({med_go:.1%})",
    annotation_position="top right", annotation_font_size=10,
)

# Quadrant labels — anchored to fixed axis bounds so they don't drift with filters
pad_x = (X_MAX - X_MIN) * 0.03
pad_y = (Y_MAX - Y_MIN) * 0.03
for text, x_side, y_side, color in [
    ("Aggressive + Accurate",    "right", "top",    ARCH_COLORS["Aggressive + Accurate"]),
    ("Aggressive + Inaccurate",  "right", "bottom", ARCH_COLORS["Aggressive + Inaccurate"]),
    ("Conservative + Accurate",  "left",  "top",    ARCH_COLORS["Conservative + Accurate"]),
    ("Conservative + Inaccurate","left",  "bottom", ARCH_COLORS["Conservative + Inaccurate"]),
]:
    ax = X_MAX - pad_x if "right" in x_side else X_MIN + pad_x
    # y axis is reversed: low DQS = top of chart, so "top" = Y_MIN
    ay = Y_MIN + pad_y if "top" in y_side else Y_MAX - pad_y
    fig.add_annotation(
        x=ax, y=ay, text=f"<b>{text}</b>",
        showarrow=False, font=dict(color=color, size=10),
        xanchor="right" if "right" in x_side else "left",
    )

fig.update_layout(
    height=560,
    xaxis=dict(
        title="Go-For-It Rate",
        tickformat=".0%",
        range=[X_MIN, X_MAX],   # fixed — never shifts with filters
    ),
    yaxis=dict(
        title="DQS — Decision Quality Score (lower = better)",
        range=[Y_MAX, Y_MIN],   # reversed: low DQS at top, fixed bounds
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    plot_bgcolor="#FAFAFA",
    paper_bgcolor="white",
    margin=dict(l=60, r=40, t=40, b=60),
    hovermode="closest",
)

st.plotly_chart(fig, use_container_width=True)

# ── Archetype breakdown ───────────────────────────────────────────────────────
st.subheader("Archetype Breakdown")
arch_cols = st.columns(4)
for i, (arch, color) in enumerate(ARCH_COLORS.items()):
    count = len(df[df["archetype"] == arch])
    pct   = count / len(df) * 100 if len(df) > 0 else 0
    with arch_cols[i]:
        st.markdown(
            f"<div style='border-left:4px solid {color}; padding:8px 12px; "
            f"background:#FAFAFA; border-radius:4px'>"
            f"<b style='color:{color}'>{arch}</b><br>"
            f"<span style='font-size:1.4em;font-weight:bold'>{count}</span> coaches "
            f"<span style='color:#78909C'>({pct:.0f}%)</span><br>"
            f"<span style='font-size:0.85em;color:#546E7A'>{ARCH_DESC[arch]}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Data table ────────────────────────────────────────────────────────────────
st.subheader("All Coaches")

sort_col = st.selectbox(
    "Sort by", ["DQS Rank", "Go-For-It Rate ↓", "Go-For-It Rate ↑",
                "ODR (best first)", "Total Decisions"],
    index=0,
)

show = df[["coach_name", "seasons", "total_decisions", "go_rate",
           "dqs", "odr", "dqs_rank", "archetype"]].copy()
show["go_rate"] = (show["go_rate"] * 100).round(1).astype(str) + "%"
show["odr"]     = (show["odr"]     * 100).round(1).astype(str) + "%"
show["dqs"]     = show["dqs"].round(5)
show.columns    = ["Coach", "Seasons", "Decisions", "Go Rate",
                   "DQS", "ODR", "DQS Rank", "Archetype"]

sort_map = {
    "DQS Rank":           ("DQS Rank", True),
    "Go-For-It Rate ↓":   ("Go Rate",  False),
    "Go-For-It Rate ↑":   ("Go Rate",  True),
    "ODR (best first)":   ("ODR",      False),
    "Total Decisions":    ("Decisions",False),
}
s_col, s_asc = sort_map[sort_col]
show = show.sort_values(s_col, ascending=s_asc)

st.dataframe(show, use_container_width=True, hide_index=True, height=420)

st.caption(
    "**DQS** (Decision Quality Score) = mean gap between optimal and actual decision WPA (Win Probability Added). "
    "Lower is better. **ODR** = % of plays where coach made the historically optimal call. "
    "Data: nflfastR play-by-play, 1999–2025, regular season only."
)
