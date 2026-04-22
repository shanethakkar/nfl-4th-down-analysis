import pandas as pd
from pathlib import Path

ROOT = Path('c:/Users/shane/Projects/NFL_4thDown')
grades = pd.read_csv(ROOT / 'outputs' / 'coach_grades.csv')

# Specific coaches of interest
names_of_interest = [
    'Andy Reid', 'Pete Carroll', 'Sean Payton', 'Sean McVay', 
    'Kyle Shanahan', 'John Harbaugh', 'Mike Tomlin', 'Bill Belichick',
    'Dan Campbell', 'Nick Sirianni', 'Matt LaFleur', 'Kevin Stefanski',
    'Ron Rivera', 'Doug Pederson', 'Lincoln Riley', 'Raheem Morris'
]

print("--- Coaches of interest ---")
for name in names_of_interest:
    match = grades[grades['coach_name'].str.lower() == name.lower()]
    if len(match) > 0:
        row = match.iloc[0]
        print(f"{row['coach_name']:25s} | seasons: {row['seasons']:11s} | decisions: {row['total_decisions']:4.0f} | DQS: {row['dqs']:.5f} | ODR: {row['odr']:.3f} | go_rate: {row['go_rate']:.3f} | rank: {row['dqs_rank']:.0f}/{len(grades)}")
    else:
        # try partial match
        partial = grades[grades['coach_name'].str.contains(name.split()[-1], case=False, na=False)]
        if len(partial) > 0:
            for _, row in partial.iterrows():
                print(f"  ~{row['coach_name']:23s} | seasons: {row['seasons']:11s} | decisions: {row['total_decisions']:4.0f} | DQS: {row['dqs']:.5f} | ODR: {row['odr']:.3f} | go_rate: {row['go_rate']:.3f} | rank: {row['dqs_rank']:.0f}/{len(grades)}")
        else:
            print(f"  NOT FOUND: {name}")

# Also check early-era go-for-it leaders to find "pioneers"
print("\n--- Analytics era coaches (2017+) by go_rate ---")
coach_seasons = pd.read_csv(ROOT / 'outputs' / 'coach_season_stats.csv')
print(coach_seasons.columns.tolist())
recent = coach_seasons[coach_seasons['season'] >= 2017].groupby('coach_name').agg(
    go_rate=('go_rate','mean'),
    dqs=('dqs','mean'),
    seasons=('season','count')
).reset_index()
print(recent[recent['seasons'] >= 3].sort_values('go_rate', ascending=False).head(10).to_string())
