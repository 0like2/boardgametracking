import requests
import xml.etree.ElementTree as ET

for bgg_id in [174430, 247030]:
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}"
    resp = requests.get(url)
    root = ET.fromstring(resp.content)
    img = root.find('.//image').text
    print(f"ID {bgg_id}: {img}")
