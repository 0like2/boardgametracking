import pandas as pd
import urllib.parse

df = pd.read_excel('inputs/games.xlsx')

search_links = []
md_lines = [
    "# BGG 게임 검색 전용 링크 (직접 클릭)",
    "API 서버 통신 이슈로 자동 조회가 차단되어, 아예 가장 빠르고 편하게 찾으실 수 있도록 **클릭 한 번으로 검색 결과를 띄워주는 링크**를 준비했습니다!",
    "아래 링크를 누른 후 나오는 게임에서 주소창의 숫자(ID)만 복사해 넣어주세요.",
    "",
    "| 한글 이름 | 영문 이름 | 출시년도 | BGG 실시간 검색 링크 |",
    "|---|---|---|---|"
]

for idx, row in df.iterrows():
    name = row['name_kr']
    en = row['name_en (reference)']
    y = row['year (reference)']
    
    query = en if pd.notna(en) and en else name
    query_encoded = urllib.parse.quote(query)
    
    search_url = f"https://boardgamegeek.com/geeksearch.php?action=search&q={query_encoded}&objecttype=boardgame"
    search_links.append(search_url)
    
    md_lines.append(f"| {name} | {en} | {y} | [BGG 검색하기]({search_url}) |")

with open('output/bgg_search_links.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))

print("Markdown artifacts created at output/bgg_search_links.md")
