import requests
from bs4 import BeautifulSoup
import re

def get_boardlife_image(url: str) -> str | None:
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        meta = soup.find('meta', property='og:image')
        if meta and meta.get('content'):
            return meta['content']
    except Exception as e:
        print(f"Error fetching boardlife: {e}")
    return None
