import json
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

# [핵심 보완] 원본 문자열에 아래 키워드가 "포함"되어 있으면 해당 별자리로 확정합니다.
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

    # 매핑 데이터 초기화
    sign_ko = "알 수 없음"
    eng_key = None

    # 포함 검사 방식으로 일치하는 별자리 찾기 (오류 최소화 방식)
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

    ranking.append({
        "rank": rank,
        "sign": sign_ko,
        "key": eng_key,  # 임시로 key를 내부에 저장해둡니다.
        "fortune": translator.translate(fortune) if fortune else "",
        "advice": translator.translate(advice) if advice else "",
        "lucky_place": translator.translate(lucky_place) if lucky_place else ""
    })

# 순위 순서대로 정렬 (1위 ~ 12위)
ranking.sort(key=lambda x: x["rank"])

# 전체 순위 텍스트 생성
top_text = [f"{item['rank']}위 {item['sign']}" for item in ranking]
ranking_text = "\n".join(top_text)

# 3. 각 별자리 key별 대응 데이터 및 텍스트 자동 생성
zodiac_data = {}
for item in ranking:
    key = item["key"]
    sign_ko = item["sign"]
    
    if key:
        message_text = f"""
오하아사 전체순위 ✨

{ranking_text}

━━━━━━━━━━

✨ {sign_ko} 운세

{item['rank']}위 {sign_ko}

{item['fortune']}
{item['advice']}

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

# 4. JSON 저장 구조 설정
data = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "ranking": [{k: v for k, v in item.items() if k != "key"} for item in ranking], # 임시 key 제외 후 저장
    "zodiac": zodiac_data
}

with open("fortune.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("포함 검사 매핑 방식으로 수정 및 데이터 수집 완료되었습니다!")
