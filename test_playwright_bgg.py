from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Tichu")
        # Wait for results: class 'collection_table'
        page.wait_for_selector(".collection_table", timeout=10000)
        # Find the first row's primary link
        link = page.locator(".collection_table .primary").first
        href = link.get_attribute("href")
        print(f"HREF: {href}")
        browser.close()

if __name__ == "__main__":
    run()
