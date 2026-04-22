"""
4th Down Decision Boundary Map — NFL 4th Down Analysis
Interactive heatmap showing the optimal 4th down call across every
field position × yards-to-go combination for any score/time situation.
Powered by an XGBoost model trained on 107,000+ plays (1999–2025).
"""

import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from model import load_models, predict_grid, apply_rules

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="4th Down Decision Map · NFL Analysis",
    page_icon="🏈",
    layout="wide",
)

st.markdown(
    "<style>div.block-container{padding-top:1.5rem;padding-bottom:1rem;}</style>",
    unsafe_allow_html=True,
)

# ── Constants ─────────────────────────────────────────────────────────────────
DEC_COLORS = {
    "go_for_it":  "#2E7D32",
    "punt":       "#546E7A",
    "field_goal": "#1565C0",
}
DEC_LABELS = {
    "go_for_it":  "Go For It",
    "punt":       "Punt",
    "field_goal": "Field Goal",
}
DEC_EMOJI = {
    "go_for_it":  "🏃",
    "punt":       "👟",
    "field_goal": "🎯",
}

# Grid: 20 yardline points × 20 ydstogo points = 400 cells
YARDLINES = list(range(2, 100, 5))   # 2,7,12,...,97  (opponent end zone end)
YDSTOGOS  = list(range(1, 21))       # 1–20

# Yardline axis labels (football style)
def yl_to_label(yl):
    if yl <= 50:
        return f"Opp {yl}"
    else:
        return f"Own {100 - yl}"

YL_LABELS = [yl_to_label(yl) for yl in YARDLINES]

# ── Model loading ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_models():
    return load_models(ROOT / "models")

models = get_models()

# ── Sidebar inputs ────────────────────────────────────────────────────────────
st.sidebar.header("Game Situation")
st.sidebar.markdown("Adjust score and time — the map updates instantly.")

score_diff = st.sidebar.slider(
    "Score differential",
    min_value=-28, max_value=28, value=0, step=1,
    help="Positive = your team is winning. 0 = tied.",
)
minutes = st.sidebar.slider(
    "Minutes remaining",
    min_value=0, max_value=60, value=30, step=1,
    format="%d min",
    help="60 = start of game, 0 = final seconds.",
)
seconds = minutes * 60

st.sidebar.divider()
st.sidebar.markdown(
    "**How to read this map**\n\n"
    "Each cell shows the optimal 4th down call for that "
    "field position and distance combination.\n\n"
    "🟢 **Green** = Go for it  \n"
    "🔵 **Blue** = Field goal  \n"
    "⚫ **Gray** = Punt\n\n"
    "**★** cells are forced by game logic (rule override) — "
    "e.g. punting with under 2 minutes trailing is mathematically irrational. "
    "The ML model's raw prediction is shown for reference.\n\n"
    "Hover over any cell for exact WPA values."
)

# ── Score / time description for the title ────────────────────────────────────
if score_diff == 0:
    score_str = "Tied game"
elif score_diff > 0:
    score_str = f"Up {score_diff}"
else:
    score_str = f"Down {abs(score_diff)}"

if minutes >= 45:
    time_str = "1st quarter"
elif minutes >= 30:
    time_str = "2nd quarter"
elif minutes >= 15:
    time_str = "3rd quarter"
elif minutes >= 7:
    time_str = "4th quarter"
elif minutes >= 2:
    time_str = "Late 4th quarter"
else:
    time_str = "Final 2 minutes"

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏈 4th Down Decision Boundary Map")
st.markdown(
    f"**{score_str} · {time_str} ({minutes} min remaining)** — "
    "showing the optimal call at every field position and distance. "
    "Use the sidebar to change the game situation."
)

# ── Compute grid ──────────────────────────────────────────────────────────────
grid = predict_grid(models, score_diff=score_diff, seconds=seconds,
                    yardlines=YARDLINES, ydstogos=YDSTOGOS)

# Pivot to 2D matrices for the heatmap
# Rows = ydstogo (1→20, top to bottom),  Cols = yardline (opp goal→own 20)
pivot_opt  = grid.pivot(index="ydstogo", columns="yardline_100",
                        values="optimal_decision")
pivot_go   = grid.pivot(index="ydstogo", columns="yardline_100", values="wpa_go")
pivot_pnt  = grid.pivot(index="ydstogo", columns="yardline_100", values="wpa_punt")
pivot_fg   = grid.pivot(index="ydstogo", columns="yardline_100", values="wpa_fg")
pivot_rule = grid.pivot(index="ydstogo", columns="yardline_100",
                        values="rule_override")

# Numeric decision matrix (for color scale)
DEC_NUM = {"go_for_it": 0, "field_goal": 1, "punt": 2}
z_num = pivot_opt.map(lambda d: DEC_NUM.get(d, 2)).values.astype(float)

# Hover text — flag rule-overridden cells
hover = np.empty_like(z_num, dtype=object)
for ri, ytg in enumerate(YDSTOGOS):
    for ci, yl in enumerate(YARDLINES):
        opt      = pivot_opt.loc[ytg, yl]
        g        = pivot_go.loc[ytg, yl]
        p        = pivot_pnt.loc[ytg, yl]
        f        = pivot_fg.loc[ytg, yl]
        is_rule  = bool(pivot_rule.loc[ytg, yl])
        rule_tag = "<br><i>★ Rule override — mathematically forced</i>" if is_rule else ""
        hover[ri, ci] = (
            f"<b>4th & {ytg} at {yl_to_label(yl)}</b><br>"
            f"<br>"
            f"<b style='color:{DEC_COLORS[opt]}'>"
            f"✅ Optimal: {DEC_LABELS[opt]}</b>"
            f"{rule_tag}<br>"
            f"<br>"
            f"🏃 Go For It:  {g:+.4f} WPA<br>"
            f"🎯 Field Goal: {f:+.4f} WPA<br>"
            f"👟 Punt:       {p:+.4f} WPA"
        )

# ── Plotly heatmap ────────────────────────────────────────────────────────────
# Custom discrete colorscale: go=green, fg=blue, punt=gray
colorscale = [
    [0.0,   "#2E7D32"],   # go_for_it  (0)
    [0.333, "#2E7D32"],
    [0.334, "#1565C0"],   # field_goal (1)
    [0.666, "#1565C0"],
    [0.667, "#78909C"],   # punt       (2)
    [1.0,   "#78909C"],
]

fig = go.Figure(go.Heatmap(
    z=z_num,
    x=YL_LABELS,
    y=[f"4th & {ytg}" for ytg in YDSTOGOS],
    colorscale=colorscale,
    zmin=0, zmax=2,
    showscale=False,
    hoverinfo="text",
    text=hover,
    xgap=1.5,
    ygap=1.5,
))

# Overlay decision emoji annotations on each cell
# Rule-overridden cells get a ★ suffix so they're visually distinct
annotations = []
for ri, ytg in enumerate(YDSTOGOS):
    for ci, yl in enumerate(YARDLINES):
        opt     = pivot_opt.loc[ytg, yl]
        is_rule = bool(pivot_rule.loc[ytg, yl])
        label   = DEC_EMOJI[opt] + ("★" if is_rule else "")
        annotations.append(dict(
            x=YL_LABELS[ci],
            y=f"4th & {ytg}",
            text=label,
            showarrow=False,
            font=dict(size=10),
            xref="x", yref="y",
        ))

fig.update_layout(
    annotations=annotations,
    height=640,
    xaxis=dict(
        title="Field Position  ← own end zone · opponent end zone →",
        side="bottom",
        tickfont=dict(size=10),
        autorange="reversed",   # opp goal on the right (intuitive)
    ),
    yaxis=dict(
        title="Yards to Go (4th & ___)",
        tickfont=dict(size=10),
        autorange="reversed",   # 4th & 1 at top
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=80, r=20, t=20, b=60),
    hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#E0E0E0"),
)

st.plotly_chart(fig, use_container_width=True)

# ── Decision distribution summary ─────────────────────────────────────────────
counts = grid["optimal_decision"].value_counts()
total  = len(grid)

st.markdown("#### Decision Breakdown Across All Situations")
c1, c2, c3 = st.columns(3)
for col, dec in zip([c1, c2, c3], ["go_for_it", "field_goal", "punt"]):
    n   = counts.get(dec, 0)
    pct = n / total * 100
    color = DEC_COLORS[dec]
    col.markdown(
        f'<div style="border-left:4px solid {color};padding:10px 14px;'
        f'background:#FAFAFA;border-radius:4px;">'
        f'<div style="font-size:1.6em;font-weight:800;color:{color};">{pct:.0f}%</div>'
        f'<div style="font-size:0.9em;font-weight:600;color:{color};">'
        f'{DEC_EMOJI[dec]} {DEC_LABELS[dec]}</div>'
        f'<div style="font-size:0.8em;color:#78909C;">of situations on the map</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    "**How this works:** An XGBoost model trained on 107,000+ NFL plays (1999–2025) "
    "predicts the expected WPA (Win Probability Added) for each possible decision "
    "(go for it / punt / field goal) at every field position and yards-to-go combination. "
    "The cell color shows which decision maximizes expected WPA for the selected "
    "score differential and time remaining. Unlike the bucket-based calculator, "
    "this model provides a continuous prediction for every exact situation. "
    "**★ cells** are rule-overridden: in extreme late-game situations where the correct "
    "decision is mathematically forced (e.g. down 7 with under 2 minutes — a punt is "
    "irrational), domain rules override the ML prediction. "
    "Data: nflfastR play-by-play, 1999–2025."
)
