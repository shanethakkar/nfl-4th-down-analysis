"""
data_loader.py
--------------
Downloads and caches nflfastR play-by-play data (1999-2024) from nflverse GitHub.
Filters to 4th down plays only and applies core cleaning logic.
"""

import io

import pandas as pd
import numpy as np
import os
import time
import requests

# ── Config ────────────────────────────────────────────────────────────────────

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv.gz"

# Seasons to load
FIRST_SEASON = 1999
LAST_SEASON  = 2025

# Columns we actually need — loading all 300+ columns is slow
KEEP_COLS = [
    # Identifiers
    "play_id", "game_id", "season", "week", "game_date",
    # Teams / coaches
    "posteam", "defteam", "home_team", "away_team",
    # Situation
    "down", "ydstogo", "yardline_100", "quarter_seconds_remaining",
    "half_seconds_remaining", "game_seconds_remaining",
    "qtr", "goal_to_go", "score_differential",
    "posteam_score", "defteam_score",
    "posteam_timeouts_remaining", "defteam_timeouts_remaining",
    # Play type / outcome
    "play_type", "rush", "pass",
    "fourth_down_converted", "fourth_down_failed",
    "field_goal_result", "punt_blocked",
    # WPA / EPA
    "epa", "wpa", "wp", "def_wp",
    "vegas_wp", "vegas_home_wp",
    # Environmental
    "roof", "surface", "temp", "wind",
    # Spread / totals
    "spread_line", "total_line",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cache_path(season: int) -> str:
    return os.path.join(RAW_DIR, f"pbp_{season}.parquet")


def _download_season(season: int) -> pd.DataFrame:
    """Download one season from nflverse and return as DataFrame."""
    url = BASE_URL.format(season=season)
    print(f"  Downloading {season}...", end=" ", flush=True)

    # pandas bare urllib doesn't send a User-Agent and can't follow GitHub's
    # release-asset redirects — use requests instead.
    resp = requests.get(url, headers={"User-Agent": "nfl-4thdown-analysis/1.0"}, timeout=120)
    resp.raise_for_status()
    df = pd.read_csv(io.BytesIO(resp.content), compression="gzip", low_memory=False)

    # Keep only columns that exist in this season's data
    cols = [c for c in KEEP_COLS if c in df.columns]
    df = df[cols]

    print(f"({len(df):,} plays)")
    return df


def load_season(season: int, force_download: bool = False) -> pd.DataFrame:
    """
    Load a single season. Uses local parquet cache if available.
    Set force_download=True to re-fetch from source.
    """
    os.makedirs(RAW_DIR, exist_ok=True)
    cache = _cache_path(season)

    if os.path.exists(cache) and not force_download:
        return pd.read_parquet(cache)

    df = _download_season(season)
    df.to_parquet(cache, index=False)
    return df


def load_all_seasons(
    first: int = FIRST_SEASON,
    last: int = LAST_SEASON,
    force_download: bool = False,
    sleep: float = 0.5,
) -> pd.DataFrame:
    """
    Load all seasons from `first` to `last` inclusive.
    Downloads missing seasons and caches as parquet for fast re-use.
    """
    print(f"Loading seasons {first}–{last}...")
    dfs = []
    for season in range(first, last + 1):
        df = load_season(season, force_download=force_download)
        dfs.append(df)
        time.sleep(sleep)  # polite delay on downloads

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal plays loaded: {len(combined):,}")
    return combined


# ── 4th Down Filter ───────────────────────────────────────────────────────────

def filter_fourth_downs(pbp: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to 4th down plays only and classify each decision:
      - go_for_it
      - punt
      - field_goal
      - (drop penalties, spikes, unknowns)
    """
    df = pbp[pbp["down"] == 4].copy()

    # Classify the decision
    conditions = [
        df["play_type"] == "punt",
        df["play_type"] == "field_goal",
        df["play_type"].isin(["run", "pass", "qb_kneel", "qb_spike"]),
    ]
    choices = ["punt", "field_goal", "go_for_it"]
    df["decision"] = np.select(conditions, choices, default=None)

    # Drop plays with no classifiable decision (penalties before snap, etc.)
    df = df[df["decision"].notna()].copy()

    # Drop plays missing key situational data
    required = ["yardline_100", "ydstogo", "score_differential",
                 "game_seconds_remaining", "wp"]
    df = df.dropna(subset=required)

    print(f"4th down plays: {len(df):,} across {df['season'].nunique()} seasons")
    print(f"Decision breakdown:\n{df['decision'].value_counts()}")

    return df.reset_index(drop=True)


# ── Recency Weights ───────────────────────────────────────────────────────────

def add_recency_weights(
    df: pd.DataFrame,
    base_year: int = LAST_SEASON,
    decay: float = 0.85,
) -> pd.DataFrame:
    """
    Add a recency weight column using exponential decay.
    Seasons closer to base_year get weight closer to 1.0.
    Older seasons get downweighted by `decay` per year.

    Example with decay=0.85:
      2024 → 1.000
      2023 → 0.850
      2022 → 0.722
      2015 → 0.272
      1999 → 0.076
    """
    df = df.copy()
    df["recency_weight"] = decay ** (base_year - df["season"])
    return df


# ── Quick Summary ─────────────────────────────────────────────────────────────

def summarize(df: pd.DataFrame) -> None:
    """Print a quick overview of a loaded DataFrame."""
    print(f"Shape: {df.shape}")
    print(f"Seasons: {df['season'].min()} – {df['season'].max()}")
    print(f"Nulls in key cols:")
    key = ["decision", "yardline_100", "ydstogo", "score_differential",
           "game_seconds_remaining", "wp", "epa", "wpa"]
    for col in key:
        if col in df.columns:
            n = df[col].isna().sum()
            print(f"  {col}: {n:,} ({n/len(df)*100:.1f}%)")


# ── Main (quick smoke test) ───────────────────────────────────────────────────

if __name__ == "__main__":
    # Load just 2023-2024 as a smoke test
    pbp = load_all_seasons(first=2023, last=2024)
    fourth = filter_fourth_downs(pbp)
    fourth = add_recency_weights(fourth)
    summarize(fourth)
