from playwright.sync_api import sync_playwright

url = "https://boardlife.co.kr/game/13426"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    page.screenshot(path="boardlife_test.png", full_page=True)
    browser.close()
