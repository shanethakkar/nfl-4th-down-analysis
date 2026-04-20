"""
features.py
-----------
Feature engineering for NFL 4th down decision analysis.
Builds game-state features and rolling team tendency features.
All rolling features use strict lags (prior games only) to prevent leakage.
"""

import pandas as pd
import numpy as np

# ── Game State Bins ───────────────────────────────────────────────────────────
# These bins mirror how coaches actually think about field position and situation.
# Used for WPA baseline computation (binned averages need enough samples per cell).

# yardline_100 = yards remaining to the opponent's end zone (100 = own end zone, 0 = about to score)
FIELD_POSITION_BINS  = [0, 20, 40, 60, 80, 100]
FIELD_POSITION_LABELS = ["red_zone", "opp_territory", "midfield", "own_territory", "deep_own"]

YDSTOGO_BINS   = [0, 1, 3, 6, 100]
YDSTOGO_LABELS = ["short_1", "short_2_3", "medium_4_6", "long_7plus"]

SCORE_DIFF_BINS   = [-100, -9, -4, -1, 1, 4, 9, 100]
SCORE_DIFF_LABELS = ["down_big", "down_one_score", "down_close",
                     "tied", "up_close", "up_one_score", "up_big"]

TIME_BINS   = [0, 120, 420, 900, 1800, 3600]
TIME_LABELS = ["two_min_drill", "late_4th", "4th_quarter", "second_half", "early_game"]


def add_game_state_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Bin continuous situational features into categorical buckets."""
    df = df.copy()

    df["field_pos_bin"] = pd.cut(
        df["yardline_100"],
        bins=FIELD_POSITION_BINS,
        labels=FIELD_POSITION_LABELS,
        include_lowest=True,
    )
    df["ydstogo_bin"] = pd.cut(
        df["ydstogo"],
        bins=YDSTOGO_BINS,
        labels=YDSTOGO_LABELS,
        include_lowest=True,
    )
    df["score_diff_bin"] = pd.cut(
        df["score_differential"],
        bins=SCORE_DIFF_BINS,
        labels=SCORE_DIFF_LABELS,
        include_lowest=True,
    )
    df["time_bin"] = pd.cut(
        df["game_seconds_remaining"],
        bins=TIME_BINS,
        labels=TIME_LABELS,
        include_lowest=True,
    )

    # Composite game state key for WPA baseline lookup
    df["game_state_key"] = (
        df["field_pos_bin"].astype(str) + "|" +
        df["ydstogo_bin"].astype(str) + "|" +
        df["score_diff_bin"].astype(str) + "|" +
        df["time_bin"].astype(str)
    )

    return df


# ── Continuous Features ───────────────────────────────────────────────────────

def add_continuous_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived continuous situational features."""
    df = df.copy()

    # Is the offense in field goal range? (roughly inside opp 38)
    df["in_fg_range"] = (df["yardline_100"] <= 38).astype(int)

    # Short yardage situation (1-2 yards to go)
    df["is_short_yardage"] = (df["ydstogo"] <= 2).astype(int)

    # Game is close (within one score)
    df["is_close_game"] = (df["score_differential"].abs() <= 8).astype(int)

    # Two-minute warning territory
    df["is_two_min"] = (df["game_seconds_remaining"] <= 120).astype(int)

    # Late game (4th quarter)
    df["is_4th_quarter"] = (df["qtr"] == 4).astype(int) if "qtr" in df.columns else 0

    # Win probability bucket (how desperate/comfortable is the offense?)
    df["wp_bucket"] = pd.cut(
        df["wp"],
        bins=[0, 0.15, 0.35, 0.65, 0.85, 1.0],
        labels=["desperate", "trailing", "competitive", "leading", "dominant"],
        include_lowest=True,
    )

    # Timeout pressure — does the offense have timeouts to burn?
    if "posteam_timeouts_remaining" in df.columns:
        df["has_timeouts"] = (df["posteam_timeouts_remaining"] > 0).astype(int)

    return df


# ── Rolling Team Tendency Features ───────────────────────────────────────────
# IMPORTANT: All rolling features use shift(1) to ensure only prior-game data
# is used. This prevents data leakage into the model.

def _compute_team_rolling(
    df: pd.DataFrame,
    team_col: str,
    stat_col: str,
    window: int,
    new_col: str,
) -> pd.DataFrame:
    """
    Compute a rolling mean of `stat_col` per team (identified by `team_col`),
    using a lagged window of `window` games. Shift ensures no leakage.
    """
    df = df.sort_values(["season", "game_date", "play_id"])

    # Aggregate to game level first (one row per team per game)
    game_level = (
        df.groupby([team_col, "game_id", "game_date", "season"])[stat_col]
        .mean()
        .reset_index()
    )
    game_level = game_level.sort_values(["season", "game_date"])

    # Rolling mean with lag — grouped by team
    game_level[new_col] = (
        game_level.groupby(team_col)[stat_col]
        .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    )

    # Merge back onto play level
    df = df.merge(
        game_level[[team_col, "game_id", new_col]],
        on=[team_col, "game_id"],
        how="left",
    )
    return df


def add_rolling_tendencies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rolling team tendency features for both offense and defense.
    Uses 3-game and 8-game windows to capture short and medium-term trends.
    """
    df = df.copy()

    # Ensure game_date exists
    if "game_date" not in df.columns:
        df["game_date"] = df["season"].astype(str) + "-" + df["week"].astype(str).str.zfill(2)

    # ── Offensive go-for-it tendency ──────────────────────────────────────────
    # Binary: did they go for it on this 4th down?
    df["went_for_it"] = (df["decision"] == "go_for_it").astype(float)

    for window, suffix in [(3, "3g"), (8, "8g")]:
        df = _compute_team_rolling(
            df, "posteam", "went_for_it",
            window=window, new_col=f"off_go_rate_{suffix}"
        )

    # ── Defensive 4th down stop rate ──────────────────────────────────────────
    # When teams go for it against this defense, how often do they stop them?
    df["fourth_stop"] = df["fourth_down_failed"].fillna(0).astype(float)
    for window, suffix in [(3, "3g"), (8, "8g")]:
        df = _compute_team_rolling(
            df, "defteam", "fourth_stop",
            window=window, new_col=f"def_stop_rate_{suffix}"
        )

    # ── Offensive EPA trend ───────────────────────────────────────────────────
    for window, suffix in [(3, "3g"), (8, "8g")]:
        df = _compute_team_rolling(
            df, "posteam", "epa",
            window=window, new_col=f"off_epa_{suffix}"
        )

    return df


# ── Season Weighting ──────────────────────────────────────────────────────────

def add_era_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a normalized season feature to let the model learn temporal trends.
    Scaled 0-1 across the full data range.
    """
    df = df.copy()
    min_s, max_s = df["season"].min(), df["season"].max()
    df["season_normalized"] = (df["season"] - min_s) / (max_s - min_s)
    return df


# ── Master Feature Builder ────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all feature engineering steps in order.
    Returns a feature-enriched DataFrame ready for modeling or WPA baseline computation.
    """
    print("Building game state bins...")
    df = add_game_state_bins(df)

    print("Adding continuous features...")
    df = add_continuous_features(df)

    print("Adding rolling team tendencies (this may take a moment)...")
    df = add_rolling_tendencies(df)

    print("Adding era/season feature...")
    df = add_era_feature(df)

    print(f"Feature engineering complete. Shape: {df.shape}")
    return df


# ── Feature List for Modeling ─────────────────────────────────────────────────

MODEL_FEATURES = [
    # Continuous situational
    "yardline_100", "ydstogo", "score_differential",
    "game_seconds_remaining", "wp",
    "in_fg_range", "is_short_yardage", "is_close_game",
    "is_two_min", "is_4th_quarter",
    # Rolling tendencies
    "off_go_rate_3g", "off_go_rate_8g",
    "def_stop_rate_3g", "def_stop_rate_8g",
    "off_epa_3g", "off_epa_8g",
    # Era
    "season_normalized",
    # Environmental (if available)
    "spread_line", "total_line",
]
