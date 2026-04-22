import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import mean_squared_error, r2_score

ROOT     = Path(__file__).resolve().parent.parent
MDL_DIR  = ROOT / 'models'
DATA_DIR = ROOT / 'data'

df = pd.read_parquet(DATA_DIR / 'fourth_downs_graded.parquet').dropna(subset=['wpa'])
df['season_norm'] = (df['season'] - 1999) / (2025 - 1999)

FEATURES  = ['yardline_100', 'ydstogo', 'score_differential',
             'game_seconds_remaining', 'season_norm']
DECISIONS = ['go_for_it', 'punt', 'field_goal']
LABELS    = {'go_for_it': 'Go For It', 'punt': 'Punt', 'field_goal': 'Field Goal'}

train_df = df[df['season'] <= 2023]
test_df  = df[df['season'] >  2023]

print('=' * 62)
print('VALIDATION RESULTS  (test set = 2024–2025 seasons)')
print('=' * 62)
print(f'{"Decision":<14} {"n_train":>8} {"n_test":>7} {"RMSE":>8} {"R²":>7}')
print('-' * 62)

for dec in DECISIONS:
    model   = joblib.load(MDL_DIR / f'xgb_{dec}.pkl')
    tr      = train_df[train_df['decision'] == dec]
    te      = test_df[test_df['decision']   == dec]
    preds   = model.predict(te[FEATURES])
    rmse    = np.sqrt(mean_squared_error(te['wpa'], preds))
    r2      = r2_score(te['wpa'], preds)
    print(f'{LABELS[dec]:<14} {len(tr):>8,} {len(te):>7,} {rmse:>8.4f} {r2:>7.3f}')

print()
print('FEATURE IMPORTANCES')
print('-' * 62)
feat_labels = {
    'yardline_100':           'Field position',
    'ydstogo':                'Yards to go',
    'score_differential':     'Score differential',
    'game_seconds_remaining': 'Time remaining',
    'season_norm':            'Season (recency)',
}
for dec in DECISIONS:
    model = joblib.load(MDL_DIR / f'xgb_{dec}.pkl')
    imps  = dict(zip(FEATURES, model.feature_importances_))
    ranked = sorted(imps.items(), key=lambda x: x[1], reverse=True)
    print(f'\n{LABELS[dec]}:')
    for feat, imp in ranked:
        print(f'  {feat_labels[feat]:<25} {imp:.3f}')

print()
print('QUICK SANITY CHECKS  (predict WPA for known situations)')
print('-' * 62)
tests = [
    ('4th & 1 at opp 1yd, tied, 4th Q',  1, 1,  0, 900),
    ('4th & 20 at own 20yd, tied, 2nd H', 80, 20, 0, 1800),
    ('4th & 3 at opp 35yd, tied, 4th Q',  35, 3,  0, 900),
    ('4th & 1 at opp 40yd, up 3, 2 min',  40, 1,  3, 120),
]
print(f'{"Situation":<42} {"Go WPA":>8} {"Punt WPA":>9} {"FG WPA":>8} {"Best":>8}')
print('-' * 80)
models_loaded = {d: joblib.load(MDL_DIR / f'xgb_{d}.pkl') for d in DECISIONS}
for label, yl, ytg, sc, sec in tests:
    row = pd.DataFrame([[yl, ytg, sc, sec, (2025-1999)/(2025-1999)]],
                       columns=FEATURES)
    wpas = {d: models_loaded[d].predict(row)[0] for d in DECISIONS}
    best = max(wpas, key=wpas.get)
    print(f'{label:<42} {wpas["go_for_it"]:>+8.4f} {wpas["punt"]:>+9.4f} '
          f'{wpas["field_goal"]:>+8.4f} {best:>8}')
