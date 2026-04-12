import requests
from bs4 import BeautifulSoup
url = "https://boardlife.co.kr/game/13426"
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
# Print all div texts that have small length, to find the stats block
for d in soup.find_all('div', class_='info-val'):
    print(d.text)
for s in soup.find_all('span'):
    if s.text and len(s.text.strip()) < 10:
        print("Span:", s.text.strip())
for d in soup.find_all('div'):
    txt = d.text.strip()
    if txt and len(txt) < 30 and ('인' in txt or '명' in txt or '분' in txt or '.' in txt):
        print("Div:", txt)
