import pandas as pd
import re

def fix_url(url):
    if pd.isna(url):
        return url
    url = str(url).strip()
    match = re.search(r'game(?:=|/)(\d+)', url)
    if match:
        game_id = match.group(1)
        return f"https://boardlife.co.kr/game/{game_id}"
    return url

file_path = 'inputs/games.xlsx'
df = pd.read_excel(file_path)
df['boardlife_url'] = df['boardlife_url'].apply(fix_url)
df.to_excel(file_path, index=False)
print("Updated URLs in inputs/games.xlsx")
