import requests
from bs4 import BeautifulSoup
import re

url = "https://boardlife.co.kr/game/13426"
#url = "https://boardlife.co.kr/game/15001"
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')

print(f"URL: {url}")
# Rating?
# Usually hidden in JS or class='star-rating' or similar?
for div in soup.find_all(text=re.compile("난이도|평점|인원|시간")):
    parent = div.parent
    if parent:
        print("MATCH:", div.strip(), "=> PARENT TEXT:", parent.text.strip())
        print("  HTML:", str(parent.parent)[:150])
