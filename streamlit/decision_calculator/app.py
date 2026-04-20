"""
4th Down Decision Calculator — NFL 4th Down Decision Analysis
Look up the historically optimal call for any 4th down situation.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="4th Down Calculator · NFL 4th Down Analysis",
    page_icon="🏈",
    layout="wide",
)


ROOT = Path(__file__).resolve().parent.parent.parent

# ── Bin definitions (must match src/features.py exactly) ──────────────────────
FIELD_BINS   = [0,  20,  40,  60,  80, 100]
FIELD_LABELS = ["red_zone", "opp_territory", "midfield", "own_territory", "deep_own"]

YDS_BINS   = [0, 1, 3,  6, 100]
YDS_LABELS = ["short_1", "short_2_3", "medium_4_6", "long_7plus"]

SCORE_BINS   = [-100, -9, -4, -1, 1, 4, 9, 100]
SCORE_LABELS = ["down_big", "down_one_score", "down_close",
                "tied", "up_close", "up_one_score", "up_big"]

TIME_BINS   = [0, 120, 420, 900, 1800, 3600]
TIME_LABELS = ["two_min_drill", "late_4th", "4th_quarter", "second_half", "early_game"]

FIELD_DISPLAY = {
    "red_zone":      "Red Zone (0–20 yds to end zone)",
    "opp_territory": "Opponent's Territory (20–40)",
    "midfield":      "Midfield (40–60)",
    "own_territory": "Own Territory (60–80)",
    "deep_own":      "Deep Own Half (80–100)",
}
YDS_DISPLAY = {
    "short_1":    "4th & 1",
    "short_2_3":  "4th & 2–3",
    "medium_4_6": "4th & 4–6",
    "long_7plus": "4th & 7+",
}
SCORE_DISPLAY = {
    "down_big":       "Down big (>8 pts)",
    "down_one_score": "Down one score (4–8)",
    "down_close":     "Down close (1–3)",
    "tied":           "Tied",
    "up_close":       "Up close (1–3)",
    "up_one_score":   "Up one score (4–8)",
    "up_big":         "Up big (>8 pts)",
}
TIME_DISPLAY = {
    "two_min_drill": "Under 2 minutes",
    "late_4th":      "2–7 minutes left",
    "4th_quarter":   "7–15 min left (4th Q)",
    "second_half":   "2nd half (15–30 min)",
    "early_game":    "1st half / early game",
}

# Field position select-slider options (left = own end zone, right = opponent end zone)
FIELD_POS_OPTIONS = [
    "Own 1",  "Own 5",  "Own 10", "Own 15", "Own 20",
    "Own 25", "Own 30", "Own 35", "Own 40", "Own 45",
    "Midfield",
    "Opp 45", "Opp 40", "Opp 35", "Opp 30", "Opp 25",
    "Opp 20", "Opp 15", "Opp 10", "Opp 5",  "Opp 1",
]
FIELD_POS_YARDS = {
    "Own 1": 99,  "Own 5": 95,  "Own 10": 90, "Own 15": 85, "Own 20": 80,
    "Own 25": 75, "Own 30": 70, "Own 35": 65, "Own 40": 60, "Own 45": 55,
    "Midfield": 50,
    "Opp 45": 45, "Opp 40": 40, "Opp 35": 35, "Opp 30": 30, "Opp 25": 25,
    "Opp 20": 20, "Opp 15": 15, "Opp 10": 10, "Opp 5": 5,   "Opp 1": 1,
}

DEC_COLORS = {
    "go_for_it": "#2E7D32",
    "field_goal": "#1565C0",
    "punt":       "#546E7A",
}
DEC_LABELS = {
    "go_for_it": "Go For It",
    "field_goal": "Field Goal",
    "punt":       "Punt",
}
DEC_EMOJI = {
    "go_for_it": "🏃",
    "field_goal": "🎯",
    "punt":       "👟",
}

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_baselines():
    df = pd.read_csv(ROOT / "outputs" / "wpa_baselines_4d.csv")
    return df

@st.cache_data
def load_2d_guide():
    df = pd.read_csv(ROOT / "outputs" / "situational_guide.csv")
    return df

def bin_value(val, bins, labels):
    """Map a numeric value to its bin label using pd.cut logic."""
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        if i == 0:
            if lo <= val <= hi:
                return labels[i]
        else:
            if lo < val <= hi:
                return labels[i]
    return labels[-1]

def lookup_4d(baselines, fp, yd, sc, tm):
    row = baselines[
        (baselines["field_pos_bin"]  == fp) &
        (baselines["ydstogo_bin"]    == yd) &
        (baselines["score_diff_bin"] == sc) &
        (baselines["time_bin"]       == tm)
    ]
    return row.iloc[0] if len(row) > 0 else None

def lookup_2d(guide, fp, yd):
    row = guide[
        (guide["field_pos_bin"] == fp) &
        (guide["ydstogo_bin"]   == yd)
    ]
    return row.iloc[0] if len(row) > 0 else None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<style>div.block-container{padding-top:1.5rem;padding-bottom:1rem;}</style>",
    unsafe_allow_html=True,
)
st.title("🏈 4th Down Decision Calculator")

baselines = load_baselines()
guide_2d  = load_2d_guide()

# ── Inputs (sidebar) ──────────────────────────────────────────────────────────
st.sidebar.header("Game Situation")

field_label = st.sidebar.select_slider(
    "Field position  ← own end zone · opp →",
    options=FIELD_POS_OPTIONS,
    value="Opp 30",
    help="Drag right to move toward the opponent's end zone.",
)
yardline = FIELD_POS_YARDS[field_label]

ydstogo = st.sidebar.slider(
    "Yards to go (4th & ___)",
    min_value=1, max_value=20, value=8,
)

score_diff = st.sidebar.slider(
    "Score differential",
    min_value=-28, max_value=28, value=-5,
    help="Positive = your team is winning. 0 = tied.",
)

minutes = st.sidebar.slider(
    "Minutes remaining",
    min_value=0, max_value=60, value=10, step=1,
    help="60 = start of game, 0 = final seconds.",
    format="%d min",
)
seconds = minutes * 60   # convert to seconds for bin lookup

# ── Map to bins ───────────────────────────────────────────────────────────────
fp_bin = bin_value(yardline,    FIELD_BINS, FIELD_LABELS)
yd_bin = bin_value(ydstogo,     YDS_BINS,   YDS_LABELS)
sc_bin = bin_value(score_diff,  SCORE_BINS, SCORE_LABELS)
tm_bin = bin_value(seconds,     TIME_BINS,  TIME_LABELS)

# Show bucket mapping in the sidebar so the main area stays uncluttered
st.sidebar.divider()
st.sidebar.caption(
    f"**Situation bucket**  \n"
    f"📍 {field_label} · {FIELD_DISPLAY[fp_bin]}  \n"
    f"📏 {YDS_DISPLAY[yd_bin]}  \n"
    f"🏆 {SCORE_DISPLAY[sc_bin]}  \n"
    f"⏱ {TIME_DISPLAY[tm_bin]}"
)

# ── Lookup ────────────────────────────────────────────────────────────────────
result_4d = lookup_4d(baselines, fp_bin, yd_bin, sc_bin, tm_bin)
result_2d = lookup_2d(guide_2d,  fp_bin, yd_bin)

# Build WPA dict — prefer 4D, fall back to 2D when needed
using_4d = result_4d is not None
wpa_values = {}

if using_4d:
    for dec, col in [("go_for_it","wpa_go"), ("punt","wpa_punt"), ("field_goal","wpa_fg")]:
        v = result_4d.get(col, np.nan)
        if pd.notna(v):
            wpa_values[dec] = float(v)
    optimal    = result_4d.get("optimal_decision")
    n_plays    = int(result_4d.get("n_total", 0)) if pd.notna(result_4d.get("n_total")) else 0
    wrong_rate = float(result_4d.get("wrong_call_rate", np.nan))
    actual_rates = {
        "go_for_it":  float(result_4d.get("pct_actual_go",   np.nan)),
        "punt":       float(result_4d.get("pct_actual_punt",  np.nan)),
        "field_goal": float(result_4d.get("pct_actual_fg",    np.nan)),
    }
elif result_2d is not None:
    # 2D fallback — reconstruct from actual rates and optimal decision
    optimal      = result_2d.get("optimal_decision")
    n_plays      = int(result_2d.get("n", 0))
    wrong_rate   = float(result_2d.get("wrong_call_rate", np.nan))
    actual_rates = {}
    # No per-decision WPA in 2D guide; show go-rate context only
else:
    optimal      = None
    n_plays      = 0
    wrong_rate   = np.nan
    actual_rates = {}

# ── Output ────────────────────────────────────────────────────────────────────
st.subheader("Optimal Call")

if optimal is None:
    st.warning(
        "⚠️ Not enough historical data for this exact situation. "
        "Try adjusting the score differential or time remaining."
    )
else:
    opt_color  = DEC_COLORS[optimal]
    opt_label  = DEC_LABELS[optimal]
    opt_emoji  = DEC_EMOJI[optimal]
    wrong_pct  = wrong_rate * 100 if pd.notna(wrong_rate) else None
    right_pct  = (1 - wrong_rate) * 100 if pd.notna(wrong_rate) else None

    # ── Three decision cards ──────────────────────────────────────────────────
    # Sort all available decisions best → worst by WPA
    if wpa_values and len(wpa_values) >= 2:
        dec_order  = sorted(wpa_values.items(), key=lambda x: x[1], reverse=True)
        best_wpa   = dec_order[0][1]
        worst_wpa  = dec_order[-1][1]
        wpa_spread = best_wpa - worst_wpa
    else:
        dec_order  = [(optimal, None)]
        best_wpa = worst_wpa = wpa_spread = None

    rank_badges = ["🥇", "🥈", "🥉"]

    # Build each card as a complete HTML string to avoid rendering issues
    # when HTML markup is embedded as a Python variable inside an f-string.
    def build_card(i, dec, wpa, actual_pct):
        is_opt  = dec == optimal
        color   = DEC_COLORS[dec]
        label   = DEC_LABELS[dec]
        emoji   = DEC_EMOJI[dec]
        badge   = "&#x2705; OPTIMAL CALL" if is_opt else (rank_badges[i] if i < 3 else "")
        border  = f"3px solid {color}" if is_opt else "1px solid #E0E0E0"
        bg      = f"{color}12"         if is_opt else "#FAFAFA"
        opacity = "1"                  if is_opt else "0.7"
        fsize   = "1.5em"              if is_opt else "1.15em"

        wpa_line = f"WPA: {wpa:+.4f}" if wpa is not None else ""

        if wpa is not None and wpa_spread and wpa_spread > 0:
            if i == 0:
                adv_color = "#2E7D32"
                adv_line  = "Best option in this situation"
            else:
                diff      = (wpa - best_wpa) * 100
                adv_color = "#B71C1C"
                adv_line  = f"{diff:+.2f}% win prob vs {DEC_LABELS[dec_order[0][0]]}"
        elif is_opt:
            adv_color = "#2E7D32"
            adv_line  = "Best option in this situation"
        else:
            adv_color = "#78909C"
            adv_line  = ""

        adv_html = (
            f'<span style="color:{adv_color};font-weight:600;">{adv_line}</span>'
            if adv_line else ""
        )

        # "Coaches chose this X% of the time" line
        if actual_pct is not None and pd.notna(actual_pct):
            chosen_pct = actual_pct * 100
            if is_opt:
                chosen_color = "#2E7D32" if chosen_pct >= 60 else "#E65100" if chosen_pct < 40 else "#546E7A"
                chosen_html  = (
                    f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #E0E0E0;'
                    f'font-size:0.78em;color:{chosen_color};font-weight:600;">'
                    f'Coaches chose this {chosen_pct:.0f}% of the time</div>'
                )
            else:
                chosen_html = (
                    f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #E0E0E0;'
                    f'font-size:0.78em;color:#B71C1C;font-weight:600;">'
                    f'&#x26A0; Coaches chose this {chosen_pct:.0f}% of the time</div>'
                )
        else:
            chosen_html = ""

        return (
            f'<div style="border:{border};border-radius:10px;background:{bg};'
            f'padding:18px 14px;text-align:center;opacity:{opacity};min-height:200px;">'
            f'<div style="font-size:0.8em;font-weight:700;color:{color};'
            f'letter-spacing:0.05em;margin-bottom:6px;">{badge}</div>'
            f'<div style="font-size:2em;">{emoji}</div>'
            f'<div style="font-size:{fsize};font-weight:700;color:{color};margin:6px 0 4px 0;">'
            f'{label}</div>'
            f'<div style="font-size:0.82em;color:#78909C;margin-bottom:6px;">{wpa_line}</div>'
            f'<div style="font-size:0.82em;line-height:1.4;">{adv_html}</div>'
            f'{chosen_html}'
            f'</div>'
        )

    card_cols = st.columns(len(dec_order))
    for i, (dec, wpa) in enumerate(dec_order):
        ap = actual_rates.get(dec)
        actual_pct = float(ap) if ap is not None and pd.notna(ap) else None
        with card_cols[i]:
            st.markdown(build_card(i, dec, wpa, actual_pct), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── "What coaches actually chose" callout ─────────────────────────────────
    # Show the full decision distribution so readers can see exactly what
    # coaches did in the wrong calls — not just how often they were wrong.
    if actual_rates and any(pd.notna(v) for v in actual_rates.values()):
        # Build ordered list: optimal first, then rest by actual frequency
        all_decs = ["go_for_it", "punt", "field_goal"]
        rows = []
        for dec in all_decs:
            ap = actual_rates.get(dec)
            if ap is not None and pd.notna(ap):
                rows.append((dec, float(ap) * 100))
        # Sort: optimal first, then descending by actual rate
        rows.sort(key=lambda x: (x[0] != optimal, -x[1]))

        bar_rows_html = ""
        for dec, pct in rows:
            is_opt    = dec == optimal
            dec_color = DEC_COLORS[dec]
            label     = DEC_LABELS[dec]
            emoji     = DEC_EMOJI[dec]
            bar_w     = max(int(pct), 1)

            if is_opt:
                badge_html = (
                    f'<span style="background:{dec_color};color:#fff;font-size:0.65em;'
                    f'font-weight:700;padding:2px 6px;border-radius:4px;'
                    f'margin-left:6px;letter-spacing:0.04em;">OPTIMAL</span>'
                )
                pct_color = dec_color
            else:
                badge_html = (
                    f'<span style="background:#FFEBEE;color:#B71C1C;font-size:0.65em;'
                    f'font-weight:700;padding:2px 6px;border-radius:4px;'
                    f'margin-left:6px;letter-spacing:0.04em;">SUBOPTIMAL</span>'
                )
                pct_color = "#B71C1C"

            bar_rows_html += (
                f'<div style="display:flex;align-items:center;margin-bottom:10px;">'
                f'<div style="width:150px;font-size:0.9em;font-weight:600;'
                f'color:{dec_color};flex-shrink:0;line-height:1.4;">'
                f'{emoji} {label}<br>{badge_html}</div>'
                f'<div style="flex:1;background:#E0E0E0;border-radius:6px;height:18px;'
                f'margin:0 12px;overflow:hidden;">'
                f'<div style="background:{dec_color};width:{bar_w}%;height:100%;'
                f'border-radius:6px;"></div>'
                f'</div>'
                f'<div style="width:38px;text-align:right;font-size:0.95em;font-weight:700;'
                f'color:{pct_color};flex-shrink:0;">{pct:.0f}%</div>'
                f'</div>'
            )

        sample_note = (
            f'Based on <b>{n_plays:,}</b> similar plays from 1999–2025 NFL seasons · '
            f'{"Full 4-D match" if using_4d else "Field position & distance match"}'
        )

        callout_html = (
            f'<div style="border:1px solid #E0E0E0;border-radius:10px;background:#FAFAFA;'
            f'padding:22px 28px;">'
            f'<div style="font-size:0.8em;font-weight:700;color:#546E7A;'
            f'letter-spacing:0.06em;text-transform:uppercase;margin-bottom:14px;">'
            f'What NFL coaches actually chose in this situation</div>'
            f'{bar_rows_html}'
            f'<div style="font-size:0.8em;color:#90A4AE;margin-top:12px;'
            f'border-top:1px solid #E0E0E0;padding-top:10px;">{sample_note}</div>'
            f'</div>'
        )
        st.markdown(callout_html, unsafe_allow_html=True)

    elif wrong_pct is not None:
        # Fallback when actual rate breakdown isn't available
        bar_color = "#B71C1C" if wrong_pct >= 50 else "#E65100" if wrong_pct >= 30 else "#F9A825"
        bar_fill  = int(wrong_pct)
        st.markdown(
            f'<div style="border:1px solid #E0E0E0;border-radius:10px;background:#FAFAFA;'
            f'padding:22px 28px;text-align:center;">'
            f'<div style="font-size:0.95em;color:#546E7A;margin-bottom:8px;font-weight:600;">'
            f'NFL coaches choose a suboptimal option in this situation</div>'
            f'<div style="font-size:3em;font-weight:800;color:{bar_color};">{wrong_pct:.0f}%</div>'
            f'<div style="font-size:0.88em;color:#78909C;margin:8px 0 14px 0;">of the time</div>'
            f'<div style="background:#E0E0E0;border-radius:6px;height:10px;width:100%;overflow:hidden;">'
            f'<div style="background:{bar_color};width:{bar_fill}%;height:100%;border-radius:6px;"></div>'
            f'</div>'
            f'<div style="font-size:0.82em;color:#90A4AE;margin-top:10px;">'
            f'Based on <b>{n_plays:,}</b> similar plays from 1999–2025 NFL seasons</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    elif result_2d is not None:
        st.info(
            f"Full WPA breakdown not available for this exact game state — "
            f"showing field position & distance averages.\n\n"
            f"**Actual go-for-it rate:** {result_2d['go_pct_actual']:.1%}  |  "
            f"**Optimal go rate:** {result_2d['go_pct_optimal']:.1%}"
        )

# ── Context footnote ──────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**How this works:** Each input is mapped to a game-state bucket (field position, "
    "yards to go, score differential, time remaining). We then look up the historical "
    "average WPA (Win Probability Added) for each decision (go for it / punt / field goal) in that bucket, "
    "weighted toward recent seasons. The decision with the highest average WPA is labeled optimal. "
    "Buckets with fewer than 10 historical plays are excluded. "
    "Data: nflfastR play-by-play, 1999–2025."
)
