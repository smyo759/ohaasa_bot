from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch()

    page = browser.new_page()

    page.goto(
        "https://www.asahi.co.jp/ohaasa/week/horoscope/",
        wait_until="networkidle"
    )

    html = page.content()

    print("さそり座" in html)
    print("かに座" in html)

    browser.close()
