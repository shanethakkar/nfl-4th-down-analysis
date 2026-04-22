"""
Figure 27 — 4th Down Conversion Rate by Distance
Shows raw conversion success rates when teams go for it on 4th down,
by yards-to-go category. Used in Article 1 to ground the WPA argument
in intuitive conversion probabilities.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fourth_downs_graded.parquet"
OUT  = ROOT / "outputs" / "figures" / "27_conversion_rates.png"

# ── Palette (matches rest of article figures) ─────────────────────────────
GREEN_DARK  = "#2d6a4f"
GREEN_MED   = "#52b788"
GREEN_LIGHT = "#b7e4c7"
GRAY_DARK   = "#343a40"
GRAY_MED    = "#6c757d"
GRAY_LIGHT  = "#dee2e6"
BG          = "#f8f9fa"

# ── Load & filter ─────────────────────────────────────────────────────────
df   = pd.read_parquet(DATA)
goes = df[df["decision"] == "go_for_it"].copy()
goes = goes.dropna(subset=["fourth_down_converted", "ydstogo_bin"])

# ── Bin order and labels ──────────────────────────────────────────────────
BIN_ORDER  = ["short_1", "short_2_3", "medium_4_6", "long_7plus"]
BIN_LABELS = ["4th & 1", "4th & 2–3", "4th & 4–6", "4th & 7+"]

# ── Compute conversion rates per bin ────────────────────────────────────
results = []
for bin_key, label in zip(BIN_ORDER, BIN_LABELS):
    subset = goes[goes["ydstogo_bin"] == bin_key]
    n      = len(subset)
    rate   = subset["fourth_down_converted"].mean() * 100
    results.append({"label": label, "rate": rate, "n": n})

stats = pd.DataFrame(results)
print(stats)

# ── Build color gradient: darker = shorter distance (higher success) ───────
colors = [GREEN_DARK, GREEN_MED, "#74c69d", GREEN_LIGHT]

# ── Plot ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=BG)
ax.set_facecolor(BG)

bars = ax.barh(
    stats["label"][::-1],
    stats["rate"][::-1],
    color=colors[::-1],
    height=0.55,
    zorder=3,
)

# Rate labels on bars
for bar, (_, row) in zip(bars, stats[::-1].iterrows()):
    rate = row["rate"]
    n    = row["n"]
    # pct label at end of bar
    ax.text(
        rate + 0.8, bar.get_y() + bar.get_height() / 2,
        f"{rate:.0f}%",
        va="center", ha="left",
        fontsize=14, fontweight="bold", color=GRAY_DARK,
    )
    # sample size as small grey annotation inside bar
    ax.text(
        1.5, bar.get_y() + bar.get_height() / 2,
        f"n = {n:,}",
        va="center", ha="left",
        fontsize=9, color="white", alpha=0.85,
    )

# 50% reference line
ax.axvline(50, color=GRAY_MED, linewidth=1.2, linestyle="--", zorder=2, alpha=0.7)
ax.text(50.4, 3.65, "50%", fontsize=9, color=GRAY_MED, va="top")

# Axis formatting
ax.set_xlim(0, 90)
ax.set_xlabel("Conversion Success Rate (%)", fontsize=11, color=GRAY_DARK, labelpad=8)
ax.tick_params(axis="y", labelsize=12, colors=GRAY_DARK)
ax.tick_params(axis="x", labelsize=10, colors=GRAY_MED)
ax.set_xticks([0, 20, 40, 60, 80])
ax.spines[["top", "right", "left"]].set_visible(False)
ax.spines["bottom"].set_color(GRAY_LIGHT)
ax.xaxis.grid(True, color=GRAY_LIGHT, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

# Title
fig.text(
    0.5, 0.97,
    "When NFL Teams Go For It — How Often Do They Convert?",
    ha="center", va="top",
    fontsize=14, fontweight="bold", color=GRAY_DARK,
)
fig.text(
    0.5, 0.90,
    "4th Down Conversion Rate by Yards to Go  ·  1999–2025 Regular Seasons",
    ha="center", va="top",
    fontsize=10, color=GRAY_MED,
)

# Bottom footnote
fig.text(
    0.5, 0.01,
    "Source: nflfastR · 1999–2025 NFL regular seasons · All go-for-it attempts on 4th down",
    ha="center", va="bottom",
    fontsize=8, color=GRAY_MED, style="italic",
)

plt.tight_layout(rect=[0, 0.04, 1, 0.88])
plt.savefig(OUT, dpi=160, bbox_inches="tight", facecolor=BG)
plt.close()
print(f"Saved → {OUT}")
