"""
Story exploration — dig for compelling narrative moments in the 4th down data.
Looks for: standout seasons, single-game swings, surprising coaches,
pivot years, playoff stakes, big individual WPA-cost plays.
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path("c:/Users/shane/Projects/NFL_4thDown")
df   = pd.read_parquet(ROOT / "data" / "fourth_downs_graded.parquet")
cs   = pd.read_csv(ROOT / "outputs" / "coach_season_stats.csv")
cg   = pd.read_csv(ROOT / "outputs" / "coach_grades.csv")

print("=" * 80)
print("1. BEST INDIVIDUAL COACH-SEASONS EVER (min 30 decisions)")
print("=" * 80)
qual_seasons = cs[cs["n_decisions"] >= 30].copy()
print(qual_seasons.nsmallest(15, "dqs")[["coach_name","season","n_decisions","dqs","odr","go_rate"]].to_string())

print("\n" + "=" * 80)
print("2. WORST INDIVIDUAL COACH-SEASONS EVER (min 30 decisions)")
print("=" * 80)
print(qual_seasons.nlargest(15, "dqs")[["coach_name","season","n_decisions","dqs","odr","go_rate"]].to_string())

print("\n" + "=" * 80)
print("3. BIGGEST YEAR-OVER-YEAR DECISION-QUALITY IMPROVEMENTS BY ONE COACH")
print("=" * 80)
cs_sorted = cs.sort_values(["coach_name","season"])
cs_sorted["dqs_prev"] = cs_sorted.groupby("coach_name")["dqs"].shift(1)
cs_sorted["dqs_delta"] = cs_sorted["dqs"] - cs_sorted["dqs_prev"]
cs_sorted["go_prev"]  = cs_sorted.groupby("coach_name")["go_rate"].shift(1)
cs_sorted["go_delta"] = cs_sorted["go_rate"] - cs_sorted["go_prev"]
big_jumps = cs_sorted[(cs_sorted["n_decisions"] >= 40) & (cs_sorted["dqs_delta"].notna())]
print("Biggest IMPROVEMENT (most negative delta = improved):")
print(big_jumps.nsmallest(10, "dqs_delta")[["coach_name","season","n_decisions","go_prev","go_rate","dqs_prev","dqs","dqs_delta"]].to_string())
print("\nBiggest GO-RATE jump in a single offseason (potential analytics conversion):")
print(big_jumps.nlargest(15, "go_delta")[["coach_name","season","n_decisions","go_prev","go_rate","dqs"]].to_string())

print("\n" + "=" * 80)
print("4. SINGLE PLAYS WITH LARGEST DECISION_GAP (worst single calls in 27 years)")
print("=" * 80)
worst_plays = df.nlargest(20, "decision_gap")[
    ["season","week","posteam","defteam","qtr","game_seconds_remaining",
     "ydstogo","yardline_100","score_differential","decision","optimal_decision",
     "wpa","decision_gap","game_id"]
]
print(worst_plays.to_string())

print("\n" + "=" * 80)
print("5. PIVOT YEAR — when did the league actually start changing?")
print("=" * 80)
league = df.groupby("season").agg(
    go_rate=("decision", lambda x: (x=="go_for_it").mean()),
    n=("decision","count"),
    mean_gap=("decision_gap","mean"),
    odr=("made_optimal","mean"),
).reset_index()
league["go_delta"] = league["go_rate"].diff()
print(league.to_string())

print("\n" + "=" * 80)
print("6. POST-BELICHICK YEARS — did the 2009 game actually move the league?")
print("=" * 80)
print(league[(league["season"] >= 2007) & (league["season"] <= 2014)].to_string())

print("\n" + "=" * 80)
print("7. NOTABLE COUNTER-NARRATIVE — analytics-era coaches who STILL underperform")
print("=" * 80)
analytics_era = cs[cs["season"] >= 2020].groupby("coach_name").agg(
    seasons=("season","count"),
    n=("n_decisions","sum"),
    dqs=("dqs","mean"),
    odr=("odr","mean"),
    go_rate=("go_rate","mean"),
).reset_index()
analytics_era = analytics_era[analytics_era["n"] >= 200]
print("Worst decision quality in analytics era (2020+):")
print(analytics_era.nlargest(10, "dqs").to_string())

print("\n" + "=" * 80)
print("8. THE BELICHICK PARADOX — break down Belichick's career by era")
print("=" * 80)
bb = cs[cs["coach_name"] == "Bill Belichick"].sort_values("season")
print(bb[["season","n_decisions","dqs","odr","go_rate"]].to_string())

print("\n" + "=" * 80)
print("9. ANDY REID specifically — Chiefs era vs Eagles era")
print("=" * 80)
ar = cs[cs["coach_name"] == "Andy Reid"].sort_values("season")
print(ar[["season","n_decisions","dqs","odr","go_rate"]].to_string())

print("\n" + "=" * 80)
print("10. TOP 5 single-game WPA cost from one bad call (recent era 2015+)")
print("=" * 80)
recent_bad = df[df["season"] >= 2015].nlargest(15, "decision_gap")[
    ["season","week","posteam","defteam","qtr","game_seconds_remaining",
     "ydstogo","yardline_100","score_differential","decision","optimal_decision",
     "wpa","decision_gap","game_id"]
]
print(recent_bad.to_string())

print("\n" + "=" * 80)
print("11. THE 'PROVE IT' SEASON — coaches whose ODR jumped 10%+ year over year")
print("=" * 80)
cs_sorted["odr_prev"] = cs_sorted.groupby("coach_name")["odr"].shift(1)
cs_sorted["odr_delta"] = cs_sorted["odr"] - cs_sorted["odr_prev"]
big_odr = cs_sorted[(cs_sorted["n_decisions"] >= 40) & (cs_sorted["odr_delta"] >= 0.10)]
print(big_odr.sort_values("odr_delta", ascending=False).head(15)[
    ["coach_name","season","n_decisions","odr_prev","odr","odr_delta","dqs"]
].to_string())

print("\n" + "=" * 80)
print("12. GO-FOR-IT FAIL RATE BY SCORE STATE — when the situation matters most")
print("=" * 80)
df["score_bin"] = pd.cut(
    df["score_differential"],
    bins=[-100,-9,-1,0,8,100],
    labels=["down 9+","down 1-8","tied","up 1-8","up 9+"],
)
late = df[(df["game_seconds_remaining"] <= 600)]  # last 10 min
late_summary = late.groupby("score_bin", observed=True).agg(
    n=("decision","count"),
    go_rate=("decision", lambda x: (x=="go_for_it").mean()),
    odr=("made_optimal","mean"),
    mean_gap=("decision_gap","mean"),
).reset_index()
print("Late-game (last 10 min) decision quality by score state:")
print(late_summary.to_string())

print("\n" + "=" * 80)
print("13. ANALYTICS-INFORMED 2018 EAGLES SUPER BOWL RUN — Doug Pederson")
print("=" * 80)
dp = cs[cs["coach_name"] == "Doug Pederson"].sort_values("season")
print(dp[["season","n_decisions","dqs","odr","go_rate"]].to_string())
