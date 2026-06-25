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

# 일본어 별자리 명칭 매핑
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

# 한국어 별자리 이름과 요청하신 영문 고유 key 매핑 (물병자리부터 염소자리 순서 + 쌍둥이자리 추가)
# *요청해주신 리스트에 쌍둥이자리가 빠져 있어, 흐름상 'gem'을 추가하여 12자리를 맞추었습니다.
KEY_MAP = {
    "물병자리": "aqr",
    "물고기자리": "psc",
    "양자리": "ari",
    "황소자리": "tau",
    "쌍둥이자리": "gem",  # 12자리 구성을 위해 추가
    "게자리": "cnc",
    "사자자리": "leo",
    "처녀자리": "vir",
    "천칭자리": "lib",
    "전갈자리": "sco",  # scorpio에서 sco로 변경
    "사수자리": "sgr",
    "염소자리": "cap"
}

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
    sign = sign_el.get_text(strip=True)
    sign_ko = SIGN_MAP.get(sign, sign)

    text = txt_el.get_text("\t", strip=True)
    parts = [x.strip() for x in text.split("\t") if x.strip()]

    fortune = parts[0] if len(parts) > 0 else ""
    advice = parts[1] if len(parts) > 1 else ""
    lucky_place = parts[-1] if len(parts) > 2 else ""

    ranking.append({
        "rank": rank,
        "sign": sign_ko,
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
    sign_ko = item["sign"]
    key = KEY_MAP.get(sign_ko)
    
    if key:
        emoji = EMOJI_MAP.get(key, "✨")
        # 전갈자리와 동일한 양식의 개별 메시지 텍스트 동적 생성
        message_text = f"""
오하아사 전체순위 ✨

{ranking_text}

━━━━━━━━━━

{sign_ko} 운세

{item['rank']}위 {sign_ko}

{item['fortune']}
{item['advice']}

🍀 {item['lucky_place']}
""".strip()

        # 딕셔너리에 데이터와 텍스트를 함께 저장
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
    "ranking": ranking,
    "zodiac": zodiac_data  # aqr, psc, sco 등 고유 key로 접근 가능한 딕셔너리
}

with open("fortune.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("모든 별자리 key 대응 운세 데이터 수집이 완료되었습니다!")
