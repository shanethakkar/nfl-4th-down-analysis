# NFL 4th Down Decision Analysis — Project Plan
# This file is the source of truth for methodology and build order.
# Cursor should follow this plan when building or editing any file in this project.

---

## Project Goal
Analyze every NFL 4th down decision from 1999–2025 to determine:
1. What the optimal decision was in each situation (based on historical WPA)
2. Which coaches make the best and worst 4th down decisions
3. A deep dive on Dan Campbell — is his aggressiveness actually justified by the data?
4. How the league has evolved over 26 years
5. Build an interactive Streamlit app for readers to explore the data themselves

---

## Data Source
- nflfastR play-by-play via nflverse GitHub (CSV.gz files, no API key needed)
- Seasons: 1999–2025 (all available regular seasons)
- Cached locally as parquet after first download
- LAST_SEASON = 2025 in data_loader.py

---

## Methodology Rules — Follow These Exactly

### Optimal Decision Framework
- Use **WPA (Win Probability Added)** — already in nflfastR — as the value metric
- For each game state bucket, compute weighted average WPA per decision type
- The decision with the highest WPA in that game state = optimal decision
- **Recency weighting:** decay=0.85 per year (2025 = 1.0, 2024 = 0.85, etc.)
  - This accounts for rule changes and evolving coaching philosophy over 26 years
- Minimum 10 plays per game state × decision cell to be included in baselines
- Season is also included as a normalized feature (0–1 scaled) so the model
  learns temporal trends directly

### Game State Bins
Always use these exact bins for consistency across notebooks:
- **Field position:** (yardline_100 = yards remaining to score) 0-20 (red_zone), 20-40 (opp_territory), 40-60 (midfield), 60-80 (own_territory), 80-100 (deep_own)
- **Yards to go:** 1 (short_1), 2-3 (short_2_3), 4-6 (medium_4_6), 7+ (long_7plus)
- **Score differential:** down_big (<-8), down_one_score (-8 to -4), down_close (-4 to -1), tied, up_close (1-4), up_one_score (4-8), up_big (>8)
- **Time remaining:** two_min_drill (<120s), late_4th (120-420s), 4th_quarter (420-900s), second_half (900-1800s), early_game (>1800s)

### Rolling Features — No Leakage Rule
- All rolling team tendency features must use shift(1) before rolling
- This ensures only prior game data is used — never the current game
- Windows: 3-game and 8-game for both offense and defense

### Train/Test Split
- This is primarily a statistical analysis project, not a predictive ML project
- If any ML model is added, use temporal split: train on 1999–2023, test on 2024–2025
- Never use random split — it leaks future rolling features into training

### Coach Grading Metrics
- **DQS (Decision Quality Score):** mean(optimal_wpa - actual_decision_wpa) — lower = better
- **ODR (Optimal Decision Rate):** % of plays where coach made the optimal call — higher = better
- Minimum 50 decisions to qualify for rankings
- Grade by head coach name, not offensive coordinator
  (Campbell sets the philosophy even if OC calls individual plays)

---

## Decisions Classified
- **go_for_it:** play_type in [run, pass, qb_kneel, qb_spike]
- **punt:** play_type == punt
- **field_goal:** play_type == field_goal
- Drop: penalties before snap, missing situational data, 2-point conversions

---

## Notebook Build Order

### ✅ 01_eda.ipynb (COMPLETE)
- Load all seasons 1999–2025, filter 4th downs, add recency weights
- League-wide decision trends chart (stacked area, 1999-2025)
- Go-for-it rate heatmap (field position × yards to go)
- WPA distribution by decision type
- Data quality checks
- Save: data/fourth_downs_clean.parquet

### ✅ 02_wpa_baselines.ipynb (COMPLETE)
- Load fourth_downs_clean.parquet
- Apply game state bins (use exact bins above)
- Compute weighted WPA baselines per game_state_key × decision
- Assign optimal decision to every play
- Compute decision_gap and made_optimal columns
- Validate: spot check known situations (e.g. 4th and 1 at opp 35 should be go)
- Charts:
  - Optimal decision heatmap (what SHOULD teams do by field pos × distance)
  - Compare optimal vs actual decision rates league-wide
- Save: data/fourth_downs_graded.parquet

### ✅ 03_coach_grading.ipynb (COMPLETE)
- Load fourth_downs_graded.parquet
- Merge coach names by season + team
- Compute DQS and ODR per coach (min 50 decisions)
- Produce ranked leaderboard — best and worst coaches
- Charts:
  - Horizontal bar chart: top 15 and bottom 15 coaches by DQS
  - Scatter plot: go-for-it rate vs DQS (does aggression correlate with quality?)
  - Scatter plot: ODR vs total decisions (volume vs accuracy)
- Highlight Dan Campbell's position in every chart
- Save: outputs/coach_grades.csv

### ✅ 04_campbell_dive.ipynb (COMPLETE)
- Load fourth_downs_graded.parquet, filter to Campbell's Lions tenure (2021–2025)
- Overall decision breakdown vs league average
- DQS vs league average comparison
- By field position: where is he most/least optimal?
- By yards to go: short yardage vs long distance decisions
- Season-over-season trend: is he improving? (2021–2025)
- 10 worst individual decisions (highest decision_gap)
- 10 best individual decisions (made optimal in high-stakes situations)
- Charts:
  - Radar/spider chart: Campbell vs league avg across situational dimensions
  - Season trend line: DQS and go-for-it rate 2021–2025
  - Annotated scatter: individual decisions plotted by WP and decision_gap
- Final verdict section: justified aggression or reckless gambling?

**NOTE — 04 2025 verification:** After re-running with last=2025, confirm the verdict
cell prints `2025` (not `2024`) as the final season in the trend line. The code uses
`by_season['season'].iloc[-1]` which should auto-update. If it still says 2024, check
that `dc` (the Campbell filter) includes `season.between(2021, 2025)` — it already does.

### 🔲 05_league_evolution.ipynb (BUILD NEXT)
Goals:
Answer: Is the NFL getting smarter on 4th down? When did the analytics revolution show
up in the data, and which teams/coaches led it?

Steps:
- Load fourth_downs_graded.parquet
- Compute go-for-it rate by season (1999–2025) for the full league
- Compute mean DQS by season — is the average coach improving over time?
- Split into three eras: Classic (1999–2009), Transition (2010–2018), Analytics (2019–2025)
  - Compare go-for-it rate, DQS, and ODR across eras (bar chart with error bars)
- Identify the 10 franchises that shifted their go-for-it rate the most from era 1 → era 3
  - These are the "analytics adopters" — useful for the article narrative
- Annotate the league go-for-it rate trend line with 3–5 key real-world events:
  - 2010: increasing analytics staff adoption leaguewide
  - 2019: "The Onside Kick" rule change and 4th down analytics papers go mainstream
  - 2021: post-COVID roster chaos, shorter prep windows, more aggressive calls
  (Note: these are approximate annotations — confirm dates before publishing)
- Compute: what is the WPA the league is leaving on the table each season?
  Sum (decision_gap) league-wide by season — is this gap shrinking?

Charts:
- **Chart 12** — `12_league_goforit_trend.png`
  Line chart: league go-for-it rate 1999–2025, annotated with key events
  Background shading for the three eras
- **Chart 13** — `13_league_dqs_by_season.png`
  Line chart: mean DQS by season (with shaded confidence interval ±1 SD)
  Dotted reference line at overall mean
  Title: "Are NFL Coaches Getting Better at 4th Down Decisions?"
- **Chart 14** — `14_era_comparison.png`
  Grouped bar chart: go-for-it rate, ODR, and DQS by era (Classic / Transition / Analytics)
- **Chart 15** — `15_wpa_left_on_table.png`
  Bar chart: total decision_gap (WPA left on table) by season league-wide
  Shows whether the collective cost of bad decisions is shrinking

Save: outputs/league_trends.csv
  Columns: season, go_rate, mean_dqs, mean_odr, total_decisions, wpa_left_on_table

---

### 🔲 06_aggressive_coaches.ipynb (BUILD AFTER 05)
Goals:
Answer: Is Campbell's aggression unique, or is there a new breed of analytically-minded
aggressive coaches? Does aggression itself predict good decisions, or is it neutral?

Steps:
- Load fourth_downs_graded.parquet and outputs/coach_grades.csv
- Rank all qualifying coaches by go-for-it rate (min 50 decisions)
- Identify the top 15 most aggressive coaches — list with DQS and ODR for each
- Identify the bottom 15 least aggressive coaches — same stats
- Quadrant analysis: split coaches into 4 archetypes using median go-rate and median DQS:
  - Aggressive + Accurate (top right) — the ideal
  - Aggressive + Inaccurate (bottom right) — gambling recklessly
  - Conservative + Accurate (top left) — leaving wins but not costing games
  - Conservative + Inaccurate (bottom left) — worst of both worlds
- Select 5 comparison coaches for deep side-by-side: Campbell + 4 others
  - Criteria: at least 3 seasons, widely known, spread across archetypes
  - Suggested: Andy Reid (aggressive+accurate), Bill Belichick (conservative+accurate),
    Mike McCarthy (conservative+inaccurate), Kyle Shanahan (aggressive+varies)
  - Use coach_grades.csv to confirm selections — pick by actual DQS not assumption
- For the 5 selected coaches, compute season-by-season go_rate and DQS
- Compute: among the top 15 most aggressive coaches, what % have DQS below league average?
  This is the headline stat for the article — answers whether aggression = quality

Charts:
- **Chart 16** — `16_aggression_archetype_quadrant.png`
  Scatter plot: go-for-it rate (x) vs DQS (y) for all 162 coaches
  Four quadrants labeled with archetype names
  Campbell and 4 comparison coaches annotated with name labels
  Median lines as quadrant dividers
  Color-coded by quadrant
- **Chart 17** — `17_top15_aggressive_coaches.png`
  Horizontal grouped bar chart: top 15 most aggressive coaches
  Bars show go-rate, and a dot/marker shows DQS rank
  Campbell highlighted in his signature red
- **Chart 18** — `18_coach_comparison_seasons.png`
  Multi-line chart: season-by-season DQS for the 5 selected comparison coaches
  Each coach a different color, Campbell always in red
  Shared x-axis = seasons where all 5 overlapped (or just plot individual tenures)

Save: outputs/aggressive_coaches.csv
  Columns: coach_name, go_rate_rank, go_rate, dqs, odr, n_decisions, archetype, seasons

---

### 🔲 07_situational_guide.ipynb (BUILD AFTER 06)
Goals:
Answer: What SHOULD coaches do in every common 4th down situation, and which situations
are most consistently mismanaged? This is the "cheat sheet" section of the article.

Steps:
- Load fourth_downs_graded.parquet
- For each field_pos_bin × ydstogo_bin cell:
  - optimal_decision (from baselines)
  - wrong_call_rate: % of actual decisions that are NOT optimal
  - mean_decision_gap: average WPA cost of wrong calls in this cell
  - n: sample size
- Rank all cells by wrong_call_rate descending → "most mismanaged situations"
- Filter to cells with n >= 50 for reliability
- Compute: if every coach made the optimal call in every situation, how many WPA would
  be gained per season on average? (total recoverable WPA)
- Break down wrong call rate by decision type:
  - Where do coaches punt when they should go?
  - Where do coaches kick a FG when they should go?
  - Where do coaches go when they should punt/kick?
- Identify the 10 specific game-state situations (field pos + yds + score + time)
  with the highest cumulative WPA being left on the table league-wide

Charts:
- **Chart 19** — `19_optimal_decision_guide.png`
  Clean heatmap: field position (rows) × yards to go (cols)
  Color = optimal decision (green=go, purple=punt, blue=FG)
  Cell text shows go-for-it rate actual vs optimal rate
  This is the "cheat sheet" — make it clean enough to screenshot and share
- **Chart 20** — `20_wrong_call_heatmap.png`
  Same grid as above but colored by wrong_call_rate (white=0%, dark red=100%)
  Title: "Where NFL Coaches Make the Most Mistakes"
- **Chart 21** — `21_top10_mismanaged.png`
  Horizontal bar chart: top 10 most mismanaged situations
  Bars = wrong_call_rate, labeled with situation description
  (e.g. "4th & 1, opp territory, tied game")
- **Chart 22** — `22_recoverable_wpa.png`
  Single annotated stat visualization (large number + context)
  "The NFL leaves X WPA on the table every season from bad 4th down calls"
  Could be a simple bar showing actual vs optimal WPA by era

Save: outputs/situational_guide.csv
  Columns: field_pos_bin, ydstogo_bin, optimal_decision, wrong_call_rate,
           mean_decision_gap, n, go_pct_actual, go_pct_optimal

---

### 🔲 streamlit/app.py (BUILD AFTER 07)
Goals:
Interactive web app embedded in the WordPress article via iframe.
Hosted on Streamlit Community Cloud (free, public).
Readers can explore the data without any code.

Embedding in WordPress:
  Use an HTML block in WordPress with:
  <iframe src="https://[your-app].streamlit.app/?embed=true"
          width="100%" height="700px" frameborder="0">
  </iframe>
  Add ?embed=true to the URL to hide the Streamlit toolbar for cleaner embedding.

File structure:
  streamlit/
    app.py             ← main entry point, tab navigation
    pages/             ← one file per tab (Streamlit multipage)
      coach_explorer.py
      decision_calculator.py
      coach_comparison.py
    data_cache.py      ← loads and caches CSV/parquet for the app
    requirements.txt   ← streamlit, pandas, plotly (use plotly here, not matplotlib)

Data inputs (read-only, from outputs/):
  outputs/coach_grades.csv
  outputs/aggressive_coaches.csv
  outputs/situational_guide.csv
  outputs/league_trends.csv
  data/fourth_downs_graded.parquet  ← for decision calculator lookups

Tab 1 — Coach Explorer (Quadrant Chart):
  - Plotly scatter: go-for-it rate (x) vs DQS (y), one dot per coach
  - Hover tooltip: coach name, team(s), seasons, rank, go-rate, DQS, ODR, archetype
  - Sidebar filters:
    - Min decisions slider (50–500, default 100)
    - Era filter: All / Traditional (1999-2018) / Analytics (2019-2025)
    - Season range slider (1999–2025)
    - Highlight specific coach by name (text input with autocomplete)
  - Quadrant lines at median go-rate and median DQS (recompute dynamically on filter)
  - Quadrant labels: Aggressive+Accurate, Conservative+Inaccurate, etc.
  - Color by archetype (Aggressive+Accurate, etc.)
  - Y-axis inverted so "better" (lower DQS) is at top
  - Below the chart: sortable data table of all coaches (filterable by archetype)

Tab 2 — 4th Down Decision Calculator:
  - User inputs via sliders/dropdowns:
    - Field position (yardline_100 slider, 1–99)
    - Yards to go (1–20)
    - Score differential (-28 to +28)
    - Seconds remaining (0–3600)
  - Output:
    - Large card: "Optimal Decision: GO FOR IT / PUNT / FIELD GOAL"
    - Bar chart: WPA by decision type in this game state (from baselines)
    - Context: "X% of coaches make the optimal call here"
    - "Decision gap if wrong: -0.023 WPA"
  - Note: calculator uses the same game_state_key bins as the analysis notebooks
    (field_pos_bin, ydstogo_bin) — not exact values — so display the bin it maps to

Tab 3 — Coach Comparison:
  - Multi-select dropdown: choose up to 5 coaches to compare
  - Line chart: season-by-season DQS for selected coaches (Plotly, hoverable)
  - Line chart: season-by-season go-for-it rate for selected coaches
  - Summary table: side-by-side stats for selected coaches
  - Default selection: Campbell + 4 comparison coaches from notebook 06

Deployment checklist:
  - Add streamlit/requirements.txt (streamlit, pandas, plotly, pyarrow)
  - App must load from CSVs not parquet where possible (faster cold start)
  - Test locally with `streamlit run streamlit/app.py` before deploying
  - Deploy via github.com/streamlit/streamlit-cloud (connect GitHub repo)

---

## Output Files
- data/fourth_downs_clean.parquet — cleaned 4th down plays (from 01)
- data/fourth_downs_graded.parquet — with optimal decision + gaps (from 02)
- outputs/coach_grades.csv — coach rankings table (from 03)
- outputs/aggressive_coaches.csv — aggressive coach analysis (from 06)
- outputs/situational_guide.csv — per-situation wrong call rates (from 07)
- outputs/league_trends.csv — season-by-season league stats (from 05)
- outputs/figures/ — all saved charts (PNG, 130 DPI), numbered 01–22

---

## Code Style Rules
- All src/ modules are importable from notebooks via sys.path.append('../src')
- Functions in src/ should be reusable across notebooks — no one-off logic in src
- Notebook cells should be short and focused — one idea per cell
- Always print shape and basic stats after loading or transforming data
- Save all charts to outputs/figures/ with descriptive filenames
- Use matplotlib + seaborn only in notebooks — no plotly (keep dependencies simple)
- Streamlit app uses plotly for interactivity — do not use matplotlib in the app

---

---

## Phase 2 — ML Model & Enhanced Visualizations
> Build on top of everything in Phase 1. Nothing from Phase 1 is removed or replaced.
> Publish the article first, then add these as a "v2" update.

---

### 🔲 08_ml_model.ipynb (Phase 2 — after article publishes)
Goals:
Train a continuous gradient boosting model that predicts WPA for each decision type
given exact (non-bucketed) game situation inputs. This replaces the bucket lookup
*only* in the Streamlit calculator — all Phase 1 analysis notebooks remain unchanged
and bucket-based so the methodology stays explainable.

Inputs:
- data/fourth_downs_graded.parquet  ← already clean and feature-engineered

Features (raw, not binned):
- yardline_100 (exact yards to opponent end zone, 1–99)
- ydstogo (exact yards to go, 1–20)
- score_differential (exact, -28 to +28)
- game_seconds_remaining (exact, 0–3600)
- season_normalized (season scaled 0–1 over 1999–2025, captures recency trend)

Target:
- Train three separate models: wpa_go, wpa_punt, wpa_fg
- Each model predicts mean WPA for that decision in the given situation
- Use only plays where that decision was actually made (same as bucket baselines)

Model choice:
- XGBoost or scikit-learn GradientBoostingRegressor
- Hyperparameter tune with 5-fold cross-validation (temporal-aware folds)

Train/test split (NO random split — temporal only):
- Train: seasons 1999–2023
- Test: seasons 2024–2025
- This prevents data leakage from rolling features and recency weighting

Validation:
- RMSE and R² on held-out 2024–2025 seasons for each model
- Compare model predictions vs bucket baseline predictions (should be close but smoother)
- Feature importance plot: which inputs matter most for each decision type?
- Calibration plot: are predicted WPA values realistic?

Output:
- models/wpa_model_go.pkl
- models/wpa_model_punt.pkl
- models/wpa_model_fg.pkl
- outputs/ml_validation.csv  ← predicted vs actual WPA on test set

Charts:
- **Chart 23** — `23_feature_importance.png`
  Horizontal bar chart: top features for each model (go / punt / FG)
  Title: "What Game Factors Matter Most for Each 4th Down Decision?"
- **Chart 24** — `24_model_vs_bucket.png`
  Scatter: bucket-baseline WPA vs model-predicted WPA per play (test set)
  Shows how much smoother/different the continuous model is
- **Chart 25** — `25_model_calibration.png`
  Calibration plot: predicted WPA decile vs actual mean WPA
  Confirms the model isn't systematically over/under-predicting

New src module:
- src/model.py
  Functions:
    load_models()         ← loads all three pkl files, cached
    predict_wpa(row)      ← returns {go, punt, fg} WPA dict for any situation
    get_optimal(row)      ← returns the decision with highest predicted WPA
    predict_grid(sc, tm)  ← predict for a 20×20 field_pos × ydstogo grid (for heatmap)

---

### 🔲 streamlit/heatmap/app.py (Phase 2 — after 08_ml_model.ipynb)
Goals:
An interactive decision boundary map — the flagship Phase 2 visualization.
Shows the full 4th down decision landscape for any score/time combination.
This is the visual that gets shared on social media.

Inputs:
- models/wpa_model_go.pkl
- models/wpa_model_punt.pkl
- models/wpa_model_fg.pkl

Layout:
- Sidebar: score differential slider (-28 to +28) and minutes remaining slider (0–60)
- Main panel: Plotly heatmap
  - X-axis: yards to go (1–20, labeled 1, 2, 3, ... 10, 15, 20)
  - Y-axis: field position (own 1 → opp 1, labeled football-style)
  - Cell color: green = go for it, blue = field goal, purple = punt
  - Cell opacity: proportional to WPA confidence (margin of victory over 2nd-best option)
  - Hover tooltip: exact WPA for all three options, optimal decision, margin

Behavior:
- When sliders change, call predict_grid(score_diff, seconds) and re-render instantly
  (model inference on a 20×20 = 400 point grid is microseconds)
- Annotate the boundary lines where optimal decision changes
- Title updates dynamically: "4th Down Decision Map — Tied Game, 2nd Quarter"

File: streamlit/heatmap/app.py
Requirements: streamlit, plotly, scikit-learn (or xgboost), joblib, pandas, numpy
Config: streamlit/heatmap/.streamlit/config.toml (light theme, same as other apps)

---

### 🔲 Upgrade decision_calculator backend (Phase 2)
Goal:
Swap the bucket CSV lookup in streamlit/decision_calculator/app.py with model inference.
The UI is completely unchanged — users don't see any difference except answers for
edge cases that had no bucket match.

Changes (decision_calculator/app.py only):
- Add: from src.model import load_models, predict_wpa, get_optimal
- Replace: lookup_4d() CSV lookup with predict_wpa(yardline, ydstogo, score_diff, seconds)
- Keep: all UI code (sliders, cards, bar chart) identical
- Add: small "Powered by ML model trained on 107,000 plays" note in the footnote
- Keep: the bucket-based fallback (result_2d) as a secondary display for context

---

### 🔲 README.md (Phase 2 — after ML work is done)
Goals:
A strong public-facing README that serves as the portfolio pitch.
This is what recruiters and hiring managers see when they click the GitHub link.

Sections:
1. **Project summary** (3–4 sentences) — what it does, why it matters, key finding
2. **Key findings** — 3–5 bullet points with actual numbers from the analysis
3. **Tech stack** — Python, nflfastR, pandas, XGBoost, Streamlit, Plotly
4. **Methodology** — brief explanation of WPA baselines, ML model, coach grading
5. **Live apps** — links to all four Streamlit apps (with screenshots)
6. **Project structure** — directory tree with one-line description per file/folder
7. **How to run locally** — conda env setup, `python streamlit/precompute.py`, launch commands
8. **Data source** — nflverse/nflfastR credit and link
9. **Limitations** — brief honest section (matches blog post limitations)

Style:
- Lead with the most interesting finding, not the methodology
- Include at least one chart image embedded directly in the README
- Keep it under 400 lines — long READMEs don't get read

---

## Limitations to Acknowledge in Blog Post
- WPA baselines are league averages — don't account for roster quality
- Small sample in rare game states makes those baselines less reliable
- Coach assignment is approximate (OC vs HC ambiguity)
- Identifies correlation not causation — poor DQS may reflect roster constraints
- Rule changes over 26 years mean early seasons are less comparable
  (mitigated by recency weighting but not eliminated)
