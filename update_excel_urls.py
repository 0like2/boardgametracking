import pandas as pd
import urllib.parse

df = pd.read_excel('inputs/games.xlsx')
def fix_url(url):
    if pd.isna(url) or not str(url).strip():
        return url
    url_str = str(url).strip()
    # Check if 'game=' is in the URL query string
    parsed = urllib.parse.urlparse(url_str)
    qs = urllib.parse.parse_qs(parsed.query)
    if 'game' in qs:
        game_id = qs['game'][0]
        return f"https://boardlife.co.kr/game/{game_id}"
    return url_str

if 'boardlife_url' in df.columns:
    df['boardlife_url'] = df['boardlife_url'].apply(fix_url)
    df.to_excel('inputs/games.xlsx', index=False)
    print("Updated games.xlsx successfully.")
