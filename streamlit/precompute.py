"""
precompute.py
-------------
Generates two small CSV files used by the Streamlit apps.
Run once after updating any analysis notebook:

    python streamlit/precompute.py

Outputs:
    outputs/wpa_baselines_4d.csv   - per-game-state WPA by decision (decision calculator)
    outputs/coach_season_stats.csv - per-coach per-season stats (coach comparison)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

import pandas as pd
import numpy as np

DATA_DIR = ROOT / "data"
OUT_DIR  = ROOT / "outputs"


# ── 1. WPA Baselines (4D: field_pos × ydstogo × score_diff × time) ───────────

def compute_baselines():
    print("Loading graded parquet...")
    df = pd.read_parquet(DATA_DIR / "fourth_downs_graded.parquet")
    print(f"  {len(df):,} plays loaded")

    # Ensure bin columns are strings (may be Categorical in parquet)
    for col in ["field_pos_bin", "ydstogo_bin", "score_diff_bin", "time_bin", "decision"]:
        df[col] = df[col].astype(str)

    graded = df.dropna(subset=["wpa", "made_optimal"])

    MIN_PLAYS = 10

    # Mean WPA per game_state_key × decision
    raw = (
        graded
        .groupby(["game_state_key", "field_pos_bin", "ydstogo_bin",
                  "score_diff_bin", "time_bin", "decision"])
        .agg(mean_wpa=("wpa", "mean"), n_plays=("wpa", "count"))
        .reset_index()
    )
    raw = raw[raw["n_plays"] >= MIN_PLAYS]

    # Pivot to wide: one row per game state, columns per decision
    wide = raw.pivot_table(
        index=["game_state_key", "field_pos_bin", "ydstogo_bin",
               "score_diff_bin", "time_bin"],
        columns="decision",
        values="mean_wpa",
    ).reset_index()
    wide.columns.name = None

    # Ensure all three decision columns exist
    for dec, col in [("go_for_it", "wpa_go"), ("punt", "wpa_punt"), ("field_goal", "wpa_fg")]:
        if dec in wide.columns:
            wide = wide.rename(columns={dec: col})
        else:
            wide[col] = np.nan

    # Total plays, wrong-call rate, and actual decision rates per game state
    state_stats = (
        graded
        .groupby("game_state_key")
        .agg(
            n_total        =("wpa",       "count"),
            wrong_call_rate=("made_optimal", lambda x: (x == 0).mean()),
            pct_actual_go  =("decision",  lambda x: (x == "go_for_it").mean()),
            pct_actual_punt=("decision",  lambda x: (x == "punt").mean()),
            pct_actual_fg  =("decision",  lambda x: (x == "field_goal").mean()),
        )
        .reset_index()
    )
    wide = wide.merge(state_stats, on="game_state_key", how="left")

    # Optimal decision (highest WPA among decisions with data)
    def get_optimal(row):
        options = {
            "go_for_it": row.get("wpa_go", np.nan),
            "punt":       row.get("wpa_punt", np.nan),
            "field_goal": row.get("wpa_fg", np.nan),
        }
        valid = {k: v for k, v in options.items() if pd.notna(v)}
        return max(valid, key=valid.get) if valid else None

    wide["optimal_decision"] = wide.apply(get_optimal, axis=1)

    out_path = OUT_DIR / "wpa_baselines_4d.csv"
    wide.to_csv(out_path, index=False)
    print(f"  Saved: {out_path.name}  ({len(wide):,} rows)")
    return wide


# ── 2. Coach Season Stats ─────────────────────────────────────────────────────

def compute_coach_season_stats():
    print("Loading graded parquet + games_coaches...")
    df = pd.read_parquet(DATA_DIR / "fourth_downs_graded.parquet")
    gc = pd.read_parquet(DATA_DIR / "raw" / "games_coaches.parquet")

    # Build (game_id, team) → coach_name lookup
    away = gc[["game_id", "away_team", "away_coach"]].rename(
        columns={"away_team": "team", "away_coach": "coach_name"})
    home = gc[["game_id", "home_team", "home_coach"]].rename(
        columns={"home_team": "team", "home_coach": "coach_name"})
    coach_map = (
        pd.concat([away, home])
        .drop_duplicates(subset=["game_id", "team"])
    )

    df = df.merge(
        coach_map[["game_id", "team", "coach_name"]],
        left_on=["game_id", "posteam"],
        right_on=["game_id", "team"],
        how="left",
    )

    graded = df.dropna(subset=["decision_gap", "coach_name"])
    print(f"  Coach match rate: {df['coach_name'].notna().mean()*100:.1f}%")

    # Per-coach, per-season stats (min 20 decisions for reliability)
    MIN_SEASON_DECISIONS = 20
    stats = (
        graded
        .groupby(["coach_name", "season"])
        .agg(
            n_decisions=("decision_gap", "count"),
            go_rate    =("decision", lambda x: (x == "go_for_it").mean()),
            punt_rate  =("decision", lambda x: (x == "punt").mean()),
            fg_rate    =("decision", lambda x: (x == "field_goal").mean()),
            dqs        =("decision_gap", "mean"),
            odr        =("made_optimal", "mean"),
        )
        .reset_index()
    )
    stats = stats[stats["n_decisions"] >= MIN_SEASON_DECISIONS]

    out_path = OUT_DIR / "coach_season_stats.csv"
    stats.to_csv(out_path, index=False)
    print(f"  Saved: {out_path.name}  ({len(stats):,} rows, "
          f"{stats['coach_name'].nunique()} coaches)")
    return stats


if __name__ == "__main__":
    print("=" * 50)
    compute_baselines()
    print()
    compute_coach_season_stats()
    print("=" * 50)
    print("Done. Commit the new CSV files in outputs/ to git before deploying.")
