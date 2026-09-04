import json
import time
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound
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
    {"keyword": "みずほ", "ko": "물병자리", "key": "aqr"},
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


def safe_translate(text):
    if not text:
        return ""

    # 전각 영문/숫자 등을 일반 문자로 정규화
    text = unicodedata.normalize("NFKC", text)

    # Google 번역이 일시적으로 결과를 반환하지 못하는 경우 재시도
    for attempt in range(2):
        try:
            result = translator.translate(text)

            if result:
                return result.strip()

        except TranslationNotFound:
            if attempt == 0:
                time.sleep(2)
            else:
                print(f"[번역 실패] 원문을 그대로 사용합니다: {text}")
                return text

        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                print(f"[번역 오류] 원문을 그대로 사용합니다: {text}")
                print(f"오류 내용: {e}")
                return text

    return text


ranking = []


# 2. 데이터 가공 및 번역
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

    # 운세와 조언을 하나의 텍스트로 묶어서 번역
    fortune_text = "\n".join(
        part for part in [fortune, advice] if part
    )

    translated_fortune = safe_translate(fortune_text)

    # 조언은 운세와 합쳐서 저장하므로 별도 필드는 비워 둠
    translated_advice = ""

    # 행운의 장소는 별도로 번역
    translated_lucky_place = safe_translate(lucky_place)

    ranking.append({
        "rank": rank,
        "sign": sign_ko,
        "key": eng_key,
        "fortune": translated_fortune,
        "advice": translated_advice,
        "lucky_place": translated_lucky_place
    })


ranking.sort(key=lambda x: x["rank"])


top_text = [f"{item['rank']}위 {item['sign']}" for item in ranking]
ranking_text = "\n".join(top_text)


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


data = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "ranking": [
        {k: v for k, v in item.items() if k != "key"}
        for item in ranking
    ],
    "zodiac": zodiac_data
}


with open("fortune.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


print("오하아사 운세 데이터 수집 및 번역 완료되었습니다!")
