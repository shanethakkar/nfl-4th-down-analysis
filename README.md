# NFL 4th Down Decision Analysis

**Are NFL coaches making optimal 4th down decisions — and is Dan Campbell actually a genius?**

A full-stack data science project analyzing every NFL 4th down play from 1999–2025 (107,000+ plays) using Win Probability Added (WPA) to grade every coach on decision quality. Built with Python, XGBoost, and Streamlit — from raw play-by-play data to three live interactive web apps.

[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Apps-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML_Model-FF6600)](https://xgboost.readthedocs.io)

---

## Key Findings

- **The analytics revolution is real but incomplete.** The NFL's go-for-it rate nearly doubled from **11.2% (1999) to 22.0% (2025)**, and the average coach's decision quality improved by 28% over that span — but teams still leave ~26 WPA on the table per season from suboptimal calls.
- **Dan Campbell is vindicated by the data.** His Lions rank **#9 out of 167 qualifying coaches** (DQS: 0.0062, ODR: 73.0%, go-rate: 28.4%) — his famous aggression is backed by above-average decision quality, not just gambling.
- **Coaches blow 4th & short in the red zone 55% of the time.** The most consistently mismanaged situation is 4th & 2–3 inside the opponent's 20 — coaches punt or kick a field goal when going for it is historically optimal more than half the time.
- **Aggression and accuracy are correlated.** Among the top 15 most aggressive coaches by go-for-it rate, the majority also score below the league average DQS — meaning the boldest coaches tend to also be the most correct.
- **The WPA gap is closing but hasn't closed.** League-wide WPA left on the table per season dropped from 37.1 (1999) to 25.7 (2025) — real progress, but still the equivalent of roughly one free win per team per season being left unclaimed.

---

## Live Apps

| App | Description |
|-----|-------------|
| [🏈 4th Down Decision Calculator](https://nfl-4th-down-calculator.streamlit.app) | Enter any game situation — get the historically optimal call with WPA comparison and what coaches actually chose |
| [📊 Coach Explorer](https://nfl-4th-down-coach-explorer.streamlit.app) | Interactive scatter of all 167 coaches by go-for-it rate vs decision quality. Filter by era, season, or search for any coach. |
| [🗺️ Decision Boundary Map](https://nfl-4th-down-heatmap.streamlit.app) | XGBoost-powered heatmap showing the optimal call at every field position and distance for any score/time combination |

> All apps embed cleanly in WordPress via `<iframe src="URL?embed=true">`.

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data | [nflfastR](https://www.nflfastr.com/) via nflverse (107k+ plays, 1999–2025) |
| Analysis | Python, pandas, numpy |
| ML Model | XGBoost (three regressors: go / punt / field goal WPA) |
| Visualization | Matplotlib, Seaborn (static), Plotly (interactive) |
| Apps | Streamlit, hosted on Streamlit Community Cloud |
| Environment | Anaconda (conda env: `nfl_4thdown`) |

---

## Methodology

### WPA Baseline Framework
For every game state defined by field position × yards to go × score differential × time remaining, we compute the **recency-weighted average WPA** for each available decision (go for it / punt / field goal). The decision with the highest WPA in that game state is labeled **optimal**. Recent seasons are down-weighted using exponential decay (0.85/year) to account for rule changes and evolving coaching philosophy.

### Coach Grading
Two metrics per coach (minimum 50 decisions to qualify):

| Metric | Definition | Direction |
|--------|-----------|-----------|
| **DQS** (Decision Quality Score) | Mean gap between optimal WPA and actual decision WPA | Lower = better |
| **ODR** (Optimal Decision Rate) | % of plays where the optimal call was made | Higher = better |

### ML Model (Phase 2)
Three XGBoost regressors trained on 107k plays (1999–2023 train, 2024–2025 test) predict continuous WPA for each decision type given exact (non-binned) game inputs: field position, yards to go, score differential, time remaining, and season. The models power the Decision Boundary Map heatmap, which updates in real time as you adjust the score and clock sliders.

Rule-based overrides handle mathematically deterministic situations (e.g. punting while down 7 with under 2 minutes is irrational regardless of field position) that are rare enough to create data sparsity in the training set.

---

## Project Structure

```
nfl-4th-down-analysis/
│
├── notebooks/                        ← Analysis pipeline (run in order)
│   ├── 01_eda.ipynb                  ← Data loading, cleaning, league-wide trends
│   ├── 02_wpa_baselines.ipynb        ← WPA baselines & optimal decision labeling
│   ├── 03_coach_grading.ipynb        ← DQS/ODR rankings for all 167 coaches
│   ├── 04_campbell_dive.ipynb        ← Dan Campbell deep dive (2021–2025)
│   ├── 05_league_evolution.ipynb     ← Analytics revolution: 1999 → 2025 trends
│   ├── 06_aggressive_coaches.ipynb   ← Archetype analysis: does aggression = quality?
│   ├── 07_situational_guide.ipynb    ← Where coaches go wrong most often
│   └── 08_ml_model.ipynb             ← XGBoost training, validation, feature importance
│
├── src/                              ← Reusable Python modules
│   ├── data_loader.py                ← Downloads/caches nflfastR data, filters 4th downs
│   ├── features.py                   ← Feature engineering, bins, recency weights
│   ├── grading.py                    ← WPA baselines and coach grading logic
│   └── model.py                      ← XGBoost loader, predict_wpa(), apply_rules()
│
├── streamlit/                        ← Three Streamlit web apps
│   ├── precompute.py                 ← Generates optimized CSVs for all apps
│   ├── coach_explorer/app.py         ← Coach quadrant scatter (all 167 coaches)
│   ├── decision_calculator/app.py    ← Situation lookup tool with decision cards
│   └── heatmap/app.py                ← XGBoost decision boundary map
│
├── outputs/                          ← Generated CSVs (committed) + figures (gitignored)
│   ├── coach_grades.csv              ← DQS/ODR for all 167 qualifying coaches
│   ├── aggressive_coaches.csv        ← Archetype classifications
│   ├── situational_guide.csv         ← Wrong-call rates by field position × distance
│   ├── league_trends.csv             ← Season-by-season league stats (1999–2025)
│   └── wpa_baselines_4d.csv          ← Pre-computed WPA for the calculator app
│
├── models/                           ← Trained XGBoost models (gitignored — large files)
├── data/                             ← Raw + cleaned parquet files (gitignored)
├── scripts/                          ← Utility and validation scripts
├── requirements.txt                  ← Core dependencies
├── requirements-ml.txt               ← ML dependencies (xgboost, scikit-learn, joblib)
└── PLAN.md                           ← Full methodology and build specification
```

---

## How to Run Locally

**1. Clone and set up the environment**
```bash
git clone https://github.com/shanethakkar/nfl-4th-down-analysis.git
cd nfl-4th-down-analysis
conda create -n nfl_4thdown python=3.11
conda activate nfl_4thdown
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

**2. Run the analysis notebooks** (in order — each saves outputs the next one needs)
```bash
jupyter notebook notebooks/01_eda.ipynb
# Data downloads automatically from nflverse on first run (~500MB, cached as parquet)
```

**3. Train the ML models** (needed for the heatmap app only)
```bash
jupyter notebook notebooks/08_ml_model.ipynb
# Saves three XGBoost models to models/ (~30 seconds on a modern laptop)
```

**4. Pre-compute app data**
```bash
python streamlit/precompute.py
```

**5. Launch the apps**
```bash
# Decision Calculator
streamlit run streamlit/decision_calculator/app.py --server.port 8510

# Coach Explorer
streamlit run streamlit/coach_explorer/app.py --server.port 8511

# Decision Boundary Map (requires trained models)
streamlit run streamlit/heatmap/app.py --server.port 8512
```

---

## Data Source

Play-by-play data from **[nflfastR](https://www.nflfastr.com/)** via the [nflverse GitHub releases](https://github.com/nflverse/nflverse-data). Free to use, no API key required. Data downloads automatically on first notebook run and is cached locally as Parquet. WPA values are pre-computed by nflfastR using a calibrated win probability model.

---

## Limitations

- WPA baselines are league averages and don't account for roster quality (having Patrick Mahomes changes the math on 4th & 5 considerably)
- Small sample sizes in rare game states (very late game, extreme score differentials) make those specific baselines less reliable — the ML model uses rule-based overrides for the most extreme cases
- Coach assignments are by head coach; offensive coordinators make individual play calls, but head coaches set the aggressive/conservative philosophy
- Analysis identifies correlation not causation — a poor DQS may reflect roster constraints, game situation selection bias, or opponent quality rather than pure decision-making error
- Rule changes over 26 years (kickoff rules, pass interference enforcement, etc.) mean early seasons are less comparable; mitigated by recency weighting but not eliminated
