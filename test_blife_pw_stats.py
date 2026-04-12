from playwright.sync_api import sync_playwright

url = "https://boardlife.co.kr/game/13426"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    
    # Let's extract the full text and find the keywords
    text = page.locator("body").inner_text()
    
    # Find contextual text
    import re
    # Rating is usually a number near "평점" or under a star
    print("Full text snippet:")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '난이도' in line or '평점' in line or '인원' in line or '시간' in line:
            print("---")
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                print(f"[{j}] {lines[j]}")
                
    browser.close()
