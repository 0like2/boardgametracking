import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import urllib.parse
from pathlib import Path

df = pd.read_excel('inputs/games.xlsx')
bgg_ids = []
bgg_links = []

for idx, row in df.iterrows():
    en_name = row['name_en (reference)']
    kr_name = row['name_kr']
    year = str(row['year (reference)'])
    
    query = en_name if pd.notna(en_name) and en_name else kr_name
    query_encoded = urllib.parse.quote(query)
    
    url = f"https://boardgamegeek.com/xmlapi2/search?query={query_encoded}&type=boardgame,boardgameexpansion"
    print(f"[{idx+1}/{len(df)}] Searching: {query} ({year})...")
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        
        best_id = ""
        best_link = ""
        found = False
        items = root.findall('item')
        if items:
            for item in items:
                item_year = item.find('yearpublished')
                if item_year is not None and item_year.attrib.get('value') == year:
                    best_id = item.attrib.get('id', '')
                    found = True
                    break
            
            if not found:
                best_id = items[0].attrib.get('id', '')
        
        if best_id:
            best_link = f"https://boardgamegeek.com/boardgame/{best_id}"
            
        bgg_ids.append(best_id)
        bgg_links.append(best_link)
            
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        bgg_ids.append("")
        bgg_links.append("")
        
    time.sleep(1.5) # respect BGG rate limit

df['bgg_id'] = bgg_ids
df['bgg_link'] = bgg_links

# Create a Markdown review file
md_lines = [
    "# BGG 게임 검색 결과 (검토용)",
    "API를 통해 찾아낸 자동 매칭 결과입니다. **BGG Link**를 클릭하여 정확한 게임이 맞는지 확인해주세요.",
    "",
    "| 한글 이름 | 영문 이름 | 출시년도 | 매칭된 BGG ID | BGG 링크 |",
    "|---|---|---|---|---|"
]

for idx, row in df.iterrows():
    name = row['name_kr']
    en = row['name_en (reference)']
    y = row['year (reference)']
    bid = bgg_ids[idx]
    link = bgg_links[idx]
    link_md = f"[바로가기]({link})" if link else "검색 실패"
    md_lines.append(f"| {name} | {en} | {y} | {bid} | {link_md} |")

# Also save the final excel
df.to_excel('inputs/games.xlsx', index=False)

with open('bgg_review.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))

