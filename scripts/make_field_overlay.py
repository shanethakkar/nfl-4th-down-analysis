"""
Figure 26 — Football Field Decision Overlay
--------------------------------------------
Shows the historically optimal 4th down call (Go For It / Field Goal / Punt)
as colored zones on four miniature football fields — one per yards-to-go
category — based on WPA baselines computed from 107,000 plays (1999–2025).

Output: outputs/figures/26_field_decision_map.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path

# ── Output path ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "outputs" / "figures" / "26_field_decision_map.png"

# ── Colors ─────────────────────────────────────────────────────────────────
COLORS = {
    "go_for_it":  "#27ae60",   # emerald green
    "field_goal": "#1f6fb2",   # steel blue
    "punt":       "#636e72",   # cool gray
}
LABELS = {
    "go_for_it":  "GO FOR IT",
    "field_goal": "FIELD GOAL",
    "punt":       "PUNT",
}

FIELD_BG     = "#2d6a31"   # rich turf green
FIELD_STRIPE = "#266229"   # subtle alternating stripe
LINE_COLOR   = "white"

# ── Decision zones ─────────────────────────────────────────────────────────
# Each row: (distance label, [(x_start, x_end, decision), ...])
# X-axis = yards from own goal line (0 = own end zone, 100 = opponent end zone)
# Based on WPA baselines from 1999–2025, averaged across all score/time situations.
ROWS = [
    ("4th & 1–3", [( 0,  20, "punt"),
                   (20, 100, "go_for_it")]),

    ("4th & 4–6", [( 0,  40, "punt"),
                   (40,  80, "go_for_it"),
                   (80, 100, "field_goal")]),

    ("4th & 7+",  [( 0,  40, "punt"),
                   (40,  60, "go_for_it"),
                   (60, 100, "field_goal")]),
]

# ── Figure layout ──────────────────────────────────────────────────────────
N         = len(ROWS)
FIG_W     = 14
FIG_H     = 7.5
STRIP_BOT = [0.60, 0.37, 0.14]      # bottom edge of each strip (figure fraction)
STRIP_H   = 0.185                    # height of each strip (figure fraction)
STRIP_L   = 0.12                     # left edge
STRIP_W   = 0.83                     # width

fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="#f7f7f7")

# ── Helper: draw one field strip ───────────────────────────────────────────
def draw_strip(ax, zones, row_label, show_yard_numbers=False):
    """Render one football-field strip with decision zone overlays."""

    # Turf background
    ax.add_patch(mpatches.Rectangle(
        (0, 0), 100, 1, facecolor=FIELD_BG, zorder=0
    ))

    # Alternating 5-yard stripes (subtle depth)
    for i in range(20):
        if i % 2 == 1:
            ax.add_patch(mpatches.Rectangle(
                (i * 5, 0), 5, 1,
                facecolor=FIELD_STRIPE, alpha=0.55, zorder=1
            ))

    # Decision zone fills
    for x0, x1, dec in zones:
        ax.add_patch(mpatches.Rectangle(
            (x0, 0), x1 - x0, 1,
            facecolor=COLORS[dec], alpha=0.80, zorder=2
        ))
        # Decision label centred in zone
        mid   = (x0 + x1) / 2
        width = x1 - x0
        fsize = 11.5 if width >= 40 else (9.5 if width >= 20 else 8)
        ax.text(
            mid, 0.50, LABELS[dec],
            ha="center", va="center",
            fontsize=fsize, fontweight="bold", color="white", zorder=6,
            path_effects=[pe.withStroke(linewidth=2.5, foreground="#00000060")]
        )

    # Zone boundary lines (bright white, on top of overlay)
    boundaries = sorted({x for x0, x1, _ in zones for x in (x0, x1)})
    for x in boundaries:
        ax.axvline(x, color="white", linewidth=2.2, alpha=0.95, zorder=5)

    # Yard lines every 10 yards
    for y in range(0, 101, 10):
        lw = 2.0 if y == 50 else 1.2
        ax.axvline(y, color=LINE_COLOR, linewidth=lw, alpha=0.75, zorder=4)

    # Subtle hash lines every 5 yards
    for y in range(5, 100, 10):
        ax.axvline(y, color=LINE_COLOR, linewidth=0.5, alpha=0.25, zorder=3)

    # Yard number labels (football field style: 10, 20, 30, 40, 50, 40, 30, 20, 10)
    yard_labels = {10:"10", 20:"20", 30:"30", 40:"40", 50:"50",
                   60:"40", 70:"30", 80:"20", 90:"10"}
    for x, lbl in yard_labels.items():
        ax.text(
            x, 0.10, lbl,
            ha="center", va="bottom",
            fontsize=7, color="white", alpha=0.65,
            fontfamily="DejaVu Sans", zorder=7
        )

    # Axes
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Distance label on the left
    ax.text(
        -0.013, 0.50, row_label,
        ha="right", va="center",
        fontsize=12.5, fontweight="bold", color="#1a1a1a",
        transform=ax.transAxes
    )


# ── Draw all strips ────────────────────────────────────────────────────────
axes = []
for i, ((row_label, zones), bot) in enumerate(zip(ROWS, STRIP_BOT)):
    ax = fig.add_axes([STRIP_L, bot, STRIP_W, STRIP_H])
    draw_strip(ax, zones, row_label)
    axes.append(ax)

# ── End-zone banners (shared, above top strip and implied at right) ─────────
top_ax = axes[0]
# Pinned to the top strip's coordinate space
top_ax.text(
    1.5, 1.22, "← YOUR END ZONE",
    ha="left", va="bottom",
    fontsize=8.5, color="#555555", style="italic",
    transform=top_ax.transData
)
top_ax.text(
    98.5, 1.22, "OPPONENT END ZONE →",
    ha="right", va="bottom",
    fontsize=8.5, color="#555555", style="italic",
    transform=top_ax.transData
)

# ── Field position labels below the bottom strip ───────────────────────────
bot_ax = axes[-1]
field_labels = {
     5: "Own 5",
    20: "Own 20",
    35: "Own 35",
    50: "Midfield",
    65: "Opp 35",
    80: "Opp 20",
    95: "Opp 5",
}
for x, lbl in field_labels.items():
    bot_ax.text(
        x, -0.28, lbl,
        ha="center", va="top",
        fontsize=8.5, color="#444444",
        transform=bot_ax.transData
    )

# ── Title ──────────────────────────────────────────────────────────────────
fig.text(
    0.5, 0.965,
    "What Should NFL Coaches Do on 4th Down?",
    ha="center", fontsize=17, fontweight="bold", color="#1a1a1a"
)
fig.text(
    0.5, 0.935,
    "Historically optimal call by field position, based on Win Probability Added (WPA) · 1999–2025 NFL data",
    ha="center", fontsize=10.5, color="#555555"
)

# ── Legend ─────────────────────────────────────────────────────────────────
legend_y  = 0.045
legend_xs = [0.27, 0.50, 0.73]
for x, (dec, color) in zip(legend_xs, COLORS.items()):
    # Pill background
    pill = mpatches.FancyBboxPatch(
        (x - 0.075, legend_y - 0.018), 0.15, 0.036,
        boxstyle="round,pad=0.005",
        facecolor=color, edgecolor="none",
        transform=fig.transFigure, zorder=5
    )
    fig.add_artist(pill)
    fig.text(
        x, legend_y, LABELS[dec],
        ha="center", va="center",
        fontsize=10, fontweight="bold", color="white",
        transform=fig.transFigure, zorder=6
    )

# ── Footnote ───────────────────────────────────────────────────────────────
fig.text(
    0.5, 0.005,
    "Source: nflfastR play-by-play data, 1999–2025  ·  Averaged across all score differentials and game times",
    ha="center", fontsize=8, color="#aaaaaa"
)

# ── Save ───────────────────────────────────────────────────────────────────
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Saved → {OUT}")
