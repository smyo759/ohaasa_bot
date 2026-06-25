import json
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

URL = "https://www.asahi.co.jp/ohaasa/week/horoscope/"

html = requests.get(URL).text

soup = BeautifulSoup(html, "html.parser")

items = soup.select("ul.oa_horoscope_list li")

print("items:", len(items))

ranking = []

translator = GoogleTranslator(
    source="ja",
    target="ko"
)

for item in items:

    rank = int(
        item.select_one(".horo_rank")
        .get_text(strip=True)
    )

    sign = (
        item.select_one(".horo_name")
        .get_text(strip=True)
    )

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
        "sign": sign,
        "fortune": translator.translate(fortune),
        "advice": translator.translate(advice),
        "lucky_place": translator.translate(lucky_place)
    })

print(ranking)

data = {
    "ranking": ranking
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
