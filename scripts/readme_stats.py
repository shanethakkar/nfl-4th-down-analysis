import pandas as pd

cg = pd.read_csv('outputs/coach_grades.csv')
print('=== COACH GRADES ===')
print('Total qualifying coaches:', len(cg[cg['total_decisions'] >= 50]))
top5 = cg.nsmallest(5, 'dqs')[['coach_name','dqs','odr','go_rate','total_decisions']]
bot5 = cg.nlargest(5, 'dqs')[['coach_name','dqs','odr','go_rate','total_decisions']]
print('Top 5 (best DQS):')
print(top5.to_string())
print('Bottom 5 (worst DQS):')
print(bot5.to_string())
dc = cg[cg['coach_name'].str.contains('Campbell', na=False)]
print('Campbell:')
print(dc[['coach_name','dqs','odr','go_rate','total_decisions']].to_string())

lt = pd.read_csv('outputs/league_trends.csv')
print('\n=== LEAGUE TRENDS ===')
print('Go rate 1999:', lt[lt['season']==1999]['go_rate'].values)
print('Go rate 2025:', lt[lt['season']==2025]['go_rate'].values)
print('WPA left 1999:', lt[lt['season']==1999]['wpa_left_on_table'].values)
print('WPA left 2025:', lt[lt['season']==2025]['wpa_left_on_table'].values)

sg = pd.read_csv('outputs/situational_guide.csv')
print('\n=== SITUATIONAL GUIDE ===')
print('Worst wrong call situations:')
print(sg.nlargest(5, 'wrong_call_rate')[['field_pos_bin','ydstogo_bin','wrong_call_rate','n']].to_string())
print('Total plays analyzed:', sg['n'].sum())
