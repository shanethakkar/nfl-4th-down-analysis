"""
src/model.py
------------
Loads the three trained XGBoost models and exposes clean prediction functions
used by both the Decision Calculator and the Heatmap Streamlit apps.

Models trained in notebooks/08_ml_model.ipynb.
Expected files:
    models/xgb_go_for_it.pkl
    models/xgb_punt.pkl
    models/xgb_field_goal.pkl

Public API
----------
load_models()                          -> dict of {decision: XGBRegressor}
predict_wpa(models, yardline, ydstogo, score_diff, seconds, season=2025)
                                       -> dict {decision: wpa_float}
apply_rules(score_diff, seconds, yardline)
                                       -> str or None  (forced decision, or None)
get_optimal(wpa_dict, score_diff, seconds, yardline)
                                       -> tuple (decision: str, rule_override: bool)
predict_grid(models, score_diff, seconds, season=2025)
                                       -> DataFrame with columns:
                                          yardline_100, ydstogo,
                                          wpa_go, wpa_punt, wpa_fg,
                                          optimal_decision, rule_override

Rule-based overrides
--------------------
ML models underperform in rare extreme late-game situations because training
data is sparse and the optimal decision is mathematically deterministic.
These rules encode domain knowledge that the data alone cannot fully capture.

Rule 1 — Can't win with a field goal (< 2 min, down > 3 pts)
    A field goal scores 3 pts. If you're down by 4+ with under 2 minutes,
    a FG can never tie the game. Going for it is the only rational path.

Rule 2 — Punting concedes the game (< 1 min, losing by any margin)
    With under 60 seconds and trailing, punting hands the ball to the
    opponent who can kneel it out. Going for it is the only path to winning.

Rule 3 — Take the points in FG range while winning (< 2 min, up, in range)
    Up by any amount with under 2 minutes inside the opponent's 35 — kicking
    a FG extends the lead and forces a 2-score response. Punting leaves
    points off the board with no logical upside.
"""

from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

# ── Constants ──────────────────────────────────────────────────────────────────
DECISIONS  = ["go_for_it", "punt", "field_goal"]
FEATURES   = ["yardline_100", "ydstogo", "score_differential",
              "game_seconds_remaining", "season_norm"]
FIRST_SEASON = 1999
LAST_SEASON  = 2025

# Grid resolution for the heatmap (yards to end zone × yards to go)
GRID_YARDLINES = list(range(1,  100, 5))   # 1,6,11,...,96  → 20 points
GRID_YDSTOGO   = list(range(1,  21,  1))   # 1–20            → 20 points


def _season_norm(season: int) -> float:
    return (season - FIRST_SEASON) / (LAST_SEASON - FIRST_SEASON)


def _model_dir() -> Path:
    """Resolve models/ directory relative to this file regardless of cwd."""
    return Path(__file__).resolve().parent.parent / "models"


# ── Public functions ───────────────────────────────────────────────────────────

def load_models(model_dir: Path | None = None) -> dict:
    """
    Load all three XGBoost models from disk.

    Returns
    -------
    dict  {decision_name: fitted XGBRegressor}

    Usage (with Streamlit caching)
    -----
        @st.cache_resource
        def get_models():
            return load_models()
    """
    if model_dir is None:
        model_dir = _model_dir()

    models = {}
    for dec in DECISIONS:
        path = Path(model_dir) / f"xgb_{dec}.pkl"
        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}\n"
                "Run notebooks/08_ml_model.ipynb first."
            )
        models[dec] = joblib.load(path)
    return models


def predict_wpa(
    models: dict,
    yardline: int | float,
    ydstogo: int | float,
    score_diff: int | float,
    seconds: int | float,
    season: int = LAST_SEASON,
) -> dict:
    """
    Predict WPA for all three decisions in any exact game situation.

    Parameters
    ----------
    models      : dict returned by load_models()
    yardline    : yards to opponent end zone (1–99)
    ydstogo     : yards needed for first down (1–20+)
    score_diff  : offensive team score minus defensive team score
    seconds     : seconds remaining in game (0–3600)
    season      : NFL season year for recency weighting (default: 2025)

    Returns
    -------
    dict  {"go_for_it": float, "punt": float, "field_goal": float}
    """
    row = pd.DataFrame([{
        "yardline_100":            float(yardline),
        "ydstogo":                 float(ydstogo),
        "score_differential":      float(score_diff),
        "game_seconds_remaining":  float(seconds),
        "season_norm":             _season_norm(season),
    }])

    return {dec: float(models[dec].predict(row[FEATURES])[0]) for dec in DECISIONS}


def apply_rules(
    score_diff: float,
    seconds: float,
    yardline: float,
) -> str | None:
    """
    Return a forced decision when domain rules make the optimal call
    mathematically deterministic, or None if no rule applies.

    Rules are intentionally conservative — they only fire in situations where
    the correct answer is unambiguous regardless of field position or distance.

    Parameters
    ----------
    score_diff : offensive score minus defensive score (negative = trailing)
    seconds    : seconds remaining in the game
    yardline   : yards to the opponent end zone (1 = opponent 1-yd line)

    Returns
    -------
    str  e.g. "go_for_it"  — the forced decision
    None                   — no rule applies; use ML prediction
    """
    # Rule 1: Down by 4+ with under 2 minutes → only a TD can tie/win
    #         A field goal (3 pts) can never overcome a 4+ point deficit.
    if seconds < 120 and score_diff <= -4:
        return "go_for_it"

    # Rule 2: Any deficit with under 60 seconds → punting concedes the game
    if seconds < 60 and score_diff < 0:
        return "go_for_it"

    # Rule 3: Winning + in FG range + under 2 minutes → take the points
    #         Only overrides "punt"; does not override "go_for_it".
    if seconds < 120 and score_diff > 0 and yardline <= 35:
        return "field_goal"

    return None


def get_optimal(
    wpa_dict: dict,
    score_diff: float | None = None,
    seconds: float | None = None,
    yardline: float | None = None,
) -> tuple[str, bool]:
    """
    Return the best decision and whether it was forced by a domain rule.

    Parameters
    ----------
    wpa_dict   : output of predict_wpa()
    score_diff : (optional) needed for rule-based override check
    seconds    : (optional) needed for rule-based override check
    yardline   : (optional) needed for rule-based override check

    Returns
    -------
    (decision: str, rule_override: bool)
        decision      — e.g. "go_for_it"
        rule_override — True if a hard rule forced the decision
    """
    # Check domain rules when context is provided
    if score_diff is not None and seconds is not None and yardline is not None:
        forced = apply_rules(score_diff, seconds, yardline)
        if forced is not None:
            return forced, True

    return max(wpa_dict, key=wpa_dict.get), False


def predict_grid(
    models: dict,
    score_diff: int | float,
    seconds: int | float,
    season: int = LAST_SEASON,
    yardlines: list | None = None,
    ydstogos:  list | None = None,
) -> pd.DataFrame:
    """
    Score a full field-position × yards-to-go grid for the heatmap app.
    Returns one row per (yardline, ydstogo) combination.

    Parameters
    ----------
    models      : dict returned by load_models()
    score_diff  : score differential (held fixed across the grid)
    seconds     : seconds remaining  (held fixed across the grid)
    season      : season year for recency weighting
    yardlines   : list of yardline_100 values (default: GRID_YARDLINES)
    ydstogos    : list of ydstogo values      (default: GRID_YDSTOGO)

    Returns
    -------
    pd.DataFrame with columns:
        yardline_100, ydstogo,
        wpa_go, wpa_punt, wpa_fg,
        optimal_decision
    """
    if yardlines is None:
        yardlines = GRID_YARDLINES
    if ydstogos is None:
        ydstogos = GRID_YDSTOGO

    # Build the full grid as a DataFrame for vectorised prediction
    grid = pd.DataFrame(
        [(yl, ytg) for yl in yardlines for ytg in ydstogos],
        columns=["yardline_100", "ydstogo"],
    )
    grid["score_differential"]     = float(score_diff)
    grid["game_seconds_remaining"] = float(seconds)
    grid["season_norm"]            = _season_norm(season)

    for dec, col in [("go_for_it", "wpa_go"), ("punt", "wpa_punt"),
                     ("field_goal", "wpa_fg")]:
        grid[col] = models[dec].predict(grid[FEATURES]).astype(float)

    ml_optimal = grid[["wpa_go", "wpa_punt", "wpa_fg"]].idxmax(axis=1).map({
        "wpa_go":   "go_for_it",
        "wpa_punt": "punt",
        "wpa_fg":   "field_goal",
    })

    # Apply rule-based overrides row by row
    def _resolve(row: pd.Series) -> tuple[str, bool]:
        forced = apply_rules(score_diff, seconds, row["yardline_100"])
        if forced is not None:
            return forced, True
        return ml_optimal[row.name], False

    resolved = grid.apply(_resolve, axis=1, result_type="expand")
    resolved.columns = ["optimal_decision", "rule_override"]
    grid = pd.concat([grid, resolved], axis=1)

    # Spatial smoothing: remove isolated singleton cells caused by model noise.
    # A cell is a singleton when all four grid neighbors (up/down/left/right)
    # have a different decision AND no rule override applies.
    # Only non-rule-override cells are eligible for smoothing.
    pivot_dec  = grid.pivot(index="ydstogo", columns="yardline_100",
                            values="optimal_decision")
    pivot_rule = grid.pivot(index="ydstogo", columns="yardline_100",
                            values="rule_override")

    yl_vals  = list(pivot_dec.columns)
    ytg_vals = list(pivot_dec.index)

    for ri, ytg in enumerate(ytg_vals):
        for ci, yl in enumerate(yl_vals):
            if pivot_rule.loc[ytg, yl]:
                continue                # never smooth rule-forced cells
            current = pivot_dec.loc[ytg, yl]
            neighbors = []
            if ri > 0:
                neighbors.append(pivot_dec.iloc[ri - 1, ci])
            if ri < len(ytg_vals) - 1:
                neighbors.append(pivot_dec.iloc[ri + 1, ci])
            if ci > 0:
                neighbors.append(pivot_dec.iloc[ri, ci - 1])
            if ci < len(yl_vals) - 1:
                neighbors.append(pivot_dec.iloc[ri, ci + 1])
            if neighbors and all(n != current for n in neighbors):
                # Isolated singleton — use the most common neighbor decision
                pivot_dec.loc[ytg, yl] = Counter(neighbors).most_common(1)[0][0]

    # Write smoothed decisions back to the grid
    smoothed = pivot_dec.stack().reset_index()
    smoothed.columns = ["ydstogo", "yardline_100", "optimal_decision"]
    grid = grid.drop(columns=["optimal_decision"]).merge(
        smoothed, on=["ydstogo", "yardline_100"], how="left"
    )

    return grid[["yardline_100", "ydstogo",
                 "wpa_go", "wpa_punt", "wpa_fg",
                 "optimal_decision", "rule_override"]]
