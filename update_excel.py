import pandas as pd

df = pd.read_excel('inputs/games.xlsx')
if 'boardlife_url' not in df.columns:
    df.insert(3, 'boardlife_url', "")
df.to_excel('inputs/games.xlsx', index=False)
