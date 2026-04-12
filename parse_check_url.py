import pandas as pd
import requests
from bs4 import BeautifulSoup

df = pd.read_excel('inputs/games.xlsx')
test_url = df.iloc[0]['boardlife_url']
print(test_url)
try:
    r = requests.get(test_url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.text, 'html.parser')
    meta = soup.find('meta', property='og:image')
    if meta:
        print("og:image =", meta.get('content'))
    else:
        print("No og:image found.")
except Exception as e:
    print(e)
