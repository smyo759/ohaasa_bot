import json
from datetime import datetime
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from playwright.sync_api import sync_playwright

URL = "https://www.asahi.co.jp/ohaasa/week/horoscope/"

with sync_playwright() as p:

    browser = p.chromium.launch()

    page = browser.new_page()

    page.goto(
        URL,
        wait_until="networkidle"
    )

    html = page.content()

    browser.close()

soup = BeautifulSoup(html, "html.parser")

items = soup.select("ul.oa_horoscope_list li")

SIGN_MAP = {
    "おひつじ座": "양자리",
    "おうし座": "황소자리",
    "ふたご座": "쌍둥이자리",
    "かに座": "게자리",
    "しし座": "사자자리",
    "おとめ座": "처녀자리",
    "てんびん座": "천칭자리",
    "さそり座": "전갈자리",
    "いて座": "사수자리",
    "やぎ座": "염소자리",
    "みずがめ座": "물병자리",
    "うお座": "물고기자리"
}

translator = GoogleTranslator(
    source="ja",
    target="ko"
)

ranking = []

for item in items:

    rank = int(
        item.select_one(".horo_rank")
        .get_text(strip=True)
    )

    sign = (
        item.select_one(".horo_name")
        .get_text(strip=True)
    )

    sign_ko = SIGN_MAP.get(sign, sign)

    text = (
        item.select_one(".horo_txt")
        .get_text("\t", strip=True)
    )

    parts = [x.strip() for x in text.split("\t") if x.strip()]

    fortune = parts[0] if len(parts) > 0 else ""
    advice = parts[1] if len(parts) > 1 else ""
    lucky_place = parts[-1] if len(parts) > 2 else ""

    ranking.append({
        "rank": rank,
        "sign": sign_ko,
        "fortune": translator.translate(fortune),
        "advice": translator.translate(advice),
        "lucky_place": translator.translate(lucky_place)
    })

scorpio = next(
    x for x in ranking
    if x["sign"] == "전갈자리"
)

data = {
    "date": page.url if False else datetime.now().strftime("%Y-%m-%d"),
    "ranking": ranking,
    "scorpio": scorpio
}

with open(
    "fortune.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )
