import json
import time
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from playwright.sync_api import sync_playwright

URL = "https://www.asahi.co.jp/ohaasa/week/horoscope/"


# 1. 웹 크롤링
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle")
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")
items = soup.select("ul.oa_horoscope_list li")


ZODIAC_MASTER = [
    {"keyword": "みずがめ", "ko": "물병자리", "key": "aqr"},
    {"keyword": "うお", "ko": "물고기자리", "key": "psc"},
    {"keyword": "おひつじ", "ko": "양자리", "key": "ari"},
    {"keyword": "おうし", "ko": "황소자리", "key": "tau"},
    {"keyword": "ふたご", "ko": "쌍둥이자리", "key": "gem"},
    {"keyword": "かに", "ko": "게자리", "key": "cnc"},
    {"keyword": "しし", "ko": "사자자리", "key": "leo"},
    {"keyword": "おとめ", "ko": "처녀자리", "key": "vir"},
    {"keyword": "てんびん", "ko": "천칭자리", "key": "lib"},
    {"keyword": "さそり", "ko": "전갈자리", "key": "sco"},
    {"keyword": "いて", "ko": "사수자리", "key": "sgr"},
    {"keyword": "やぎ", "ko": "염소자리", "key": "cap"}
]


translator = GoogleTranslator(source="ja", target="ko")


def normalize_text(text):
    """
    전각 문자 등을 일반 문자로 정규화하고
    앞뒤 공백을 제거한다.
    """
    if not text:
        return ""

    return unicodedata.normalize("NFKC", text).strip()


def translate_text(text, label=""):
    """
    텍스트를 한국어로 번역한다.
    번역 실패 시 최대 3번 시도하고,
    모두 실패하면 원문을 사용한다.
    """
    if not text:
        return ""

    text = normalize_text(text)

    for attempt in range(3):
        try:
            result = translator.translate(text)

            if result:
                return result.strip()

        except Exception as e:
            print(
                f"[번역 실패 {attempt + 1}/3] "
                f"{label}: {e}"
            )

            if attempt < 2:
                time.sleep(2)

    print(
        f"[최종 번역 실패] "
        f"{label} - 원문을 사용합니다."
    )

    return text


ranking = []


# 2. 데이터 가공
raw_items = []

for item in items:
    rank_el = item.select_one(".horo_rank")
    sign_el = item.select_one(".horo_name")
    txt_el = item.select_one(".horo_txt")

    if not (rank_el and sign_el and txt_el):
        continue

    rank = int(rank_el.get_text(strip=True))
    sign_ja = sign_el.get_text(strip=True)

    sign_ko = "알 수 없음"
    eng_key = None

    for info in ZODIAC_MASTER:
        if info["keyword"] in sign_ja:
            sign_ko = info["ko"]
            eng_key = info["key"]
            break

    text = txt_el.get_text("\t", strip=True)
    parts = [x.strip() for x in text.split("\t") if x.strip()]

    fortune = parts[0] if len(parts) > 0 else ""
    advice = parts[1] if len(parts) > 1 else ""
    lucky_place = parts[-1] if len(parts) > 2 else ""

    raw_items.append({
        "rank": rank,
        "sign": sign_ko,
        "key": eng_key,
        "fortune": fortune,
        "advice": advice,
        "lucky_place": lucky_place
    })


raw_items.sort(key=lambda x: x["rank"])


# 3. 운세 + 조언 / 행운의 장소 번역
for item in raw_items:

    # 운세와 조언을 하나의 문장으로 합친다.
    combined_fortune = "\n".join(
        part
        for part in [
            normalize_text(item["fortune"]),
            normalize_text(item["advice"])
        ]
        if part
    )

    print(
        f"[번역] {item['rank']}위 "
        f"{item['sign']} 운세/조언 번역 중..."
    )

    translated_fortune = translate_text(
        combined_fortune,
        f"{item['rank']}위 {item['sign']} 운세"
    )

    time.sleep(1)

    print(
        f"[번역] {item['rank']}위 "
        f"{item['sign']} 행운의 장소 번역 중..."
    )

    translated_lucky_place = translate_text(
        item["lucky_place"],
        f"{item['rank']}위 {item['sign']} 행운의 장소"
    )

    time.sleep(1)


    # 4. 번역 결과 적용
    ranking.append({
        "rank": item["rank"],
        "sign": item["sign"],
        "key": item["key"],
        "fortune": translated_fortune,
        "advice": "",
        "lucky_place": translated_lucky_place
    })


ranking.sort(key=lambda x: x["rank"])


# 5. 전체 순위 텍스트
top_text = [
    f"{item['rank']}위 {item['sign']}"
    for item in ranking
]

ranking_text = "\n".join(top_text)


# 6. 별자리별 데이터 생성
zodiac_data = {}

for item in ranking:
    key = item["key"]
    sign_ko = item["sign"]

    if key:
        message_text = f"""
오하아사 전체순위 ✨

{ranking_text}

━━━━━━━━━━

{item['rank']}위 {sign_ko}

{item['fortune']}

🍀 {item['lucky_place']}
""".strip()

        zodiac_data[key] = {
            "rank": item["rank"],
            "sign": sign_ko,
            "fortune": item["fortune"],
            "advice": item["advice"],
            "lucky_place": item["lucky_place"],
            "message": message_text
        }


# 7. JSON 생성
data = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "ranking": [
        {
            k: v
            for k, v in item.items()
            if k != "key"
        }
        for item in ranking
    ],
    "zodiac": zodiac_data
}


with open("fortune.json", "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )
    f.write("\n")


print("오하아사 운세 데이터 수집 및 번역 완료되었습니다!")
