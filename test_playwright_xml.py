from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        response = page.goto("https://boardgamegeek.com/xmlapi2/thing?id=284083&stats=1", wait_until="domcontentloaded")
        print("Status:", response.status)
        print("Content:", page.content()[:200])
    except Exception as e:
        print("Error:", e)
    browser.close()
