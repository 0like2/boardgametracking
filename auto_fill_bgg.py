import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time

df = pd.read_excel('inputs/games.xlsx')
bgg_ids = []

headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}

for idx, row in df.iterrows():
    name = row['name_kr']
    en = row['name_en (reference)']
    y = row['year (reference)']
    
    query_str = en if pd.notna(en) and en else name
    # Add year to narrow down result matching
    ddq = f'site:boardgamegeek.com/boardgame "{query_str}"' 
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(ddq)}"
    
    print(f"[{idx+1}/{len(df)}] Searching DDG for: {query_str}...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        found_id = ""
        for a in soup.find_all('a', class_='result__url'):
            href = a.get('href', '')
            decoded = urllib.parse.unquote(href)
            # Look for boardgamegeek.com/boardgame/123456
            match = re.search(r'boardgamegeek\.com/boardgame/(\d+)', decoded)
            if match:
                found_id = match.group(1)
                break
                
        bgg_ids.append(found_id)
        if found_id:
            print(f"  -> Found ID: {found_id}")
        else:
            print(f"  -> Not found")
    except Exception as e:
        print(f"  -> Error: {e}")
        bgg_ids.append("")
        
    time.sleep(1.0)

df['bgg_id'] = bgg_ids
df.to_excel('inputs/games.xlsx', index=False)
print("Finished auto-filling BGG IDs!")
