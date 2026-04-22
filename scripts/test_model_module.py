"""Quick smoke-test for src/model.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from model import load_models, predict_wpa, get_optimal, predict_grid

print('Loading models...')
models = load_models()
print(f'  Loaded {len(models)} models: {list(models.keys())}')

print()
print('predict_wpa() tests:')
tests = [
    ('4th & 1 at opp 1yd, tied, 4th Q',  1,  1,  0, 900),
    ('4th & 20 at own 20yd, tied, 2nd H', 80, 20, 0, 1800),
    ('4th & 3 at opp 35yd, tied, 4th Q',  35,  3, 0, 900),
    ('4th & 1 at opp 40yd, up 3, 2 min',  40,  1, 3, 120),
]
for label, yl, ytg, sc, sec in tests:
    wpas    = predict_wpa(models, yl, ytg, sc, sec)
    optimal = get_optimal(wpas)
    print(f'  {label}')
    print(f'    go={wpas["go_for_it"]:+.4f}  punt={wpas["punt"]:+.4f}  '
          f'fg={wpas["field_goal"]:+.4f}  → {optimal}')

print()
print('predict_grid() test (score=0, 30 min remaining):')
grid = predict_grid(models, score_diff=0, seconds=1800)
print(f'  Grid shape: {grid.shape}')
print(f'  Columns: {list(grid.columns)}')
print(f'  Optimal decision counts:')
print(grid['optimal_decision'].value_counts().to_string())
print()
print('  Sample rows:')
print(grid.head(6).to_string(index=False))
print()
print('All tests passed.')
