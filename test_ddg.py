import requests
from bs4 import BeautifulSoup
import re

query = 'site:boardgamegeek.com/boardgame "The Crew: The Quest for Planet Nine"'
url = f"https://html.duckduckgo.com/html/?q={query}"
headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', class_='result__url'):
    href = a.get('href', '')
    print(href)

