import requests
from bs4 import BeautifulSoup

def extract_image(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.text, 'html.parser')

    meta_img = soup.find('meta', property='og:image')
    if meta_img and 'content' in meta_img.attrs:
        img_url = meta_img['content']
        print(f"URL: {url} -> Image: {img_url}")

extract_image("https://boardlife.co.kr/game/21111")
extract_image("https://boardlife.co.kr/game/15001")
extract_image("https://boardlife.co.kr/game/9450")   # 루트
extract_image("https://boardlife.co.kr/game/17173")  # 용사가 죽었다
