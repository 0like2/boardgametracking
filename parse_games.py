import pandas as pd

with open('/tmp/raw_list.txt', 'r', encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

games = []
i = 0
while i < len(lines):
    if lines[i].endswith('년'):
        if i >= 3 and lines[i-3] == lines[i-2]:
            kr_name = lines[i-3]
            en_name = lines[i-1]
            year = lines[i][:4]
            # Standard columns for games.xlsx
            games.append({
                "bgg_id": "", 
                "name_kr": kr_name, 
                "shelf_location": "", 
                "name_en (reference)": en_name, 
                "year (reference)": year
            })
    i += 1

df = pd.DataFrame(games)
df.to_excel('inputs/games.xlsx', index=False)
