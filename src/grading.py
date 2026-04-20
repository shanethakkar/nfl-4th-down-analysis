"""
grading.py
----------
Computes WPA baselines per game state and grades coach decision quality.
Produces Decision Quality Score (DQS) and Optimal Decision Rate (ODR) per coach.
"""

import pandas as pd
import numpy as np
from typing import Optional

# ── WPA Baseline Computation ──────────────────────────────────────────────────

def compute_wpa_baselines(
    df: pd.DataFrame,
    weight_col: Optional[str] = "recency_weight",
) -> pd.DataFrame:
    """
    For each game_state_key × decision combination, compute the weighted average WPA.
    This becomes the "historical expected value" of each decision in each situation.

    Returns a DataFrame with columns:
        game_state_key | decision | mean_wpa | n_plays
    """
    if weight_col and weight_col in df.columns:
        # Weighted mean WPA per game state + decision
        def weighted_mean(group):
            w = group[weight_col]
            wpa = group["wpa"]
            return (wpa * w).sum() / w.sum()

        baselines = (
            df.groupby(["game_state_key", "decision"])
            .apply(lambda g: pd.Series({
                "mean_wpa": weighted_mean(g),
                "n_plays": len(g),
            }))
            .reset_index()
        )
    else:
        baselines = (
            df.groupby(["game_state_key", "decision"])
            .agg(mean_wpa=("wpa", "mean"), n_plays=("wpa", "count"))
            .reset_index()
        )

    # Only keep game states with enough data to be reliable
    MIN_PLAYS = 10
    baselines = baselines[baselines["n_plays"] >= MIN_PLAYS]

    print(f"WPA baselines computed: {len(baselines):,} game_state × decision cells")
    return baselines


def assign_optimal_decision(
    df: pd.DataFrame,
    baselines: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each play, look up the optimal decision (highest WPA in that game state)
    from the baselines table and attach it to the play.

    Also computes:
        - optimal_wpa: WPA of the best available decision
        - actual_wpa: WPA of the decision actually made
        - decision_gap: optimal_wpa - actual_wpa (lower = better coach decision)
        - made_optimal: 1 if coach made the optimal decision, else 0
    """
    # Best decision per game state
    optimal = (
        baselines.loc[baselines.groupby("game_state_key")["mean_wpa"].idxmax()]
        [["game_state_key", "decision", "mean_wpa"]]
        .rename(columns={"decision": "optimal_decision", "mean_wpa": "optimal_wpa"})
    )

    # Actual decision WPA from baselines
    actual_baseline = baselines.rename(
        columns={"decision": "decision_check", "mean_wpa": "baseline_actual_wpa"}
    )

    df = df.merge(optimal, on="game_state_key", how="left")

    # Merge actual decision's baseline WPA
    df = df.merge(
        actual_baseline[["game_state_key", "decision_check", "baseline_actual_wpa"]],
        left_on=["game_state_key", "decision"],
        right_on=["game_state_key", "decision_check"],
        how="left",
    ).drop(columns=["decision_check"])

    # Decision gap — how much WPA did the coach leave on the table?
    df["decision_gap"] = df["optimal_wpa"] - df["baseline_actual_wpa"]

    # Binary: did coach make the optimal call?
    df["made_optimal"] = (df["decision"] == df["optimal_decision"]).astype(int)

    return df


# ── Coach Identification ───────────────────────────────────────────────────────

def add_coach_info(df: pd.DataFrame, coach_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge head coach names onto plays by team + season.

    coach_df should have columns: [season, team, coach_name]
    You can build this from nflreadr::load_coaches() or a manual CSV.
    """
    df = df.merge(
        coach_df[["season", "team", "coach_name"]],
        left_on=["season", "posteam"],
        right_on=["season", "team"],
        how="left",
    ).drop(columns=["team"])
    return df


# ── Coach Grading ─────────────────────────────────────────────────────────────

def grade_coaches(
    df: pd.DataFrame,
    min_decisions: int = 50,
    coach_col: str = "coach_name",
) -> pd.DataFrame:
    """
    Compute Decision Quality Score (DQS) and Optimal Decision Rate (ODR) per coach.

    DQS = mean decision_gap (lower = better; coach consistently picks near-optimal calls)
    ODR = % of plays where coach made the optimal decision

    Returns a ranked DataFrame.
    """
    df_valid = df.dropna(subset=["decision_gap", "made_optimal", coach_col])

    graded = (
        df_valid.groupby(coach_col)
        .agg(
            total_decisions=("decision_gap", "count"),
            dqs=("decision_gap", "mean"),           # lower = better
            odr=("made_optimal", "mean"),            # higher = better
            go_rate=("decision", lambda x: (x == "go_for_it").mean()),
            punt_rate=("decision", lambda x: (x == "punt").mean()),
            fg_rate=("decision", lambda x: (x == "field_goal").mean()),
            mean_wp=("wp", "mean"),                  # avg WP in their 4th down situations
            seasons=("season", lambda x: f"{x.min()}–{x.max()}"),
        )
        .reset_index()
    )

    # Filter coaches with enough decisions to be meaningful
    graded = graded[graded["total_decisions"] >= min_decisions]

    # Rank by DQS (ascending — lower gap = better)
    graded["dqs_rank"] = graded["dqs"].rank(ascending=True).astype(int)
    graded["odr_rank"] = graded["odr"].rank(ascending=False).astype(int)

    graded = graded.sort_values("dqs_rank")

    return graded.reset_index(drop=True)


# ── Dan Campbell Deep Dive ────────────────────────────────────────────────────

def campbell_deep_dive(df: pd.DataFrame, coach_col: str = "coach_name") -> dict:
    """
    Focused analysis of Dan Campbell's 4th down decisions.
    Returns a dict of DataFrames for different slices of his decision-making.
    """
    dc = df[df[coach_col].str.contains("Campbell", na=False)].copy()

    if len(dc) == 0:
        print("Warning: No Dan Campbell plays found. Check coach_col and data.")
        return {}

    print(f"Dan Campbell 4th down decisions: {len(dc):,} plays")
    print(f"Seasons: {dc['season'].min()}–{dc['season'].max()}")

    results = {}

    # Overall decision breakdown
    results["overall"] = dc["decision"].value_counts(normalize=True).rename("rate")

    # Decision quality vs league average
    league_dqs = df["decision_gap"].mean()
    dc_dqs = dc["decision_gap"].mean()
    results["dqs_comparison"] = pd.Series({
        "campbell_dqs": dc_dqs,
        "league_avg_dqs": league_dqs,
        "difference": dc_dqs - league_dqs,
        "campbell_better": dc_dqs < league_dqs,
    })

    # By field position — where is he most/least optimal?
    results["by_field_position"] = (
        dc.groupby("field_pos_bin")
        .agg(
            decisions=("decision_gap", "count"),
            go_rate=("decision", lambda x: (x == "go_for_it").mean()),
            dqs=("decision_gap", "mean"),
            odr=("made_optimal", "mean"),
        )
        .reset_index()
    )

    # By yards to go
    results["by_ydstogo"] = (
        dc.groupby("ydstogo_bin")
        .agg(
            decisions=("decision_gap", "count"),
            go_rate=("decision", lambda x: (x == "go_for_it").mean()),
            dqs=("decision_gap", "mean"),
            odr=("made_optimal", "mean"),
        )
        .reset_index()
    )

    # Year over year trend — is he getting better?
    results["by_season"] = (
        dc.groupby("season")
        .agg(
            decisions=("decision_gap", "count"),
            go_rate=("decision", lambda x: (x == "go_for_it").mean()),
            dqs=("decision_gap", "mean"),
            odr=("made_optimal", "mean"),
        )
        .reset_index()
    )

    # His worst decisions (highest decision_gap = left most WPA on table)
    results["worst_decisions"] = (
        dc.nlargest(20, "decision_gap")
        [[
            "season", "week", "game_id", "yardline_100", "ydstogo",
            "score_differential", "game_seconds_remaining",
            "decision", "optimal_decision", "decision_gap", "wp"
        ]]
    )

    # His best decisions (made optimal call in high-stakes situations)
    results["best_decisions"] = (
        dc[dc["made_optimal"] == 1]
        .nlargest(20, "wp")
        [[
            "season", "week", "game_id", "yardline_100", "ydstogo",
            "score_differential", "game_seconds_remaining",
            "decision", "optimal_decision", "decision_gap", "wp"
        ]]
    )

    return results


# ── League-Wide Summary ───────────────────────────────────────────────────────

def league_4th_down_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    High level summary of 4th down decision trends league-wide by season.
    Good for the intro section of the blog post.
    """
    return (
        df.groupby("season")
        .agg(
            total_4th_downs=("decision", "count"),
            go_rate=("decision", lambda x: (x == "go_for_it").mean()),
            punt_rate=("decision", lambda x: (x == "punt").mean()),
            fg_rate=("decision", lambda x: (x == "field_goal").mean()),
            avg_ydstogo=("ydstogo", "mean"),
            avg_yardline=("yardline_100", "mean"),
        )
        .reset_index()
    )
