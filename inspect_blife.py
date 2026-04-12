from playwright.sync_api import sync_playwright

def intercept(response):
    if "json" in response.url or "api" in response.url or "info" in response.url or "detail" in response.url:
        print(f"XHR: {response.url} [{response.status}]")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", intercept)
    page.goto("https://boardlife.co.kr/game/13426", wait_until="networkidle")
    browser.close()
