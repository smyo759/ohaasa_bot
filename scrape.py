import json
import time
import re
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


def translate_long_text(text):
    """
    여러 문장을 하나의 번역 요청으로 처리한다.
    """
    if not text:
        return ""

    text = normalize_text(text)

    for attempt in range(2):
        try:
            result = translator.translate(text)

            if result:
                return result.strip()

        except TranslationNotFound:
            if attempt == 0:
                print("[번역 재시도] Google 번역 결과를 받지 못했습니다.")
                time.sleep(2)
            else:
                print("[전체 번역 실패] 원문을 그대로 사용합니다.")
                return text

        except Exception as e:
            if attempt == 0:
                print("[번역 재시도] 오류가 발생했습니다.")
                print(f"오류 내용: {e}")
                time.sleep(2)
            else:
                print("[전체 번역 오류] 원문을 그대로 사용합니다.")
                print(f"오류 내용: {e}")
                return text

    return text


def parse_numbered_translation(text, count):
    """
    [1], [2], [3] ... 형식으로 번역된 텍스트를
    각각의 항목으로 분리한다.

    예:
    [1]
    번역문 1

    [2]
    번역문 2
    """

    results = [""] * count

    if not text:
        return results

    pattern = re.compile(
        r"\[\s*(\d+)\s*\]\s*(.*?)(?=\[\s*\d+\s*\]|$)",
        re.DOTALL
    )

    matches = pattern.findall(text)

    for number, content in matches:
        index = int(number) - 1

        if 0 <= index < count:
            results[index] = content.strip()

    return results


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


# 3. 운세 + 조언 번역
def translate_in_batches(items, field, batch_size=3):
    """
    항목을 3개씩 묶어서 번역한다.
    일반적인 경우 번역 요청을 크게 줄이면서도
    한 번에 너무 긴 텍스트를 보내지 않도록 한다.
    """

    results = [""] * len(items)

    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]

        blocks = []

        for item in batch:
            if field == "fortune":
                fortune = normalize_text(item["fortune"])
                advice = normalize_text(item["advice"])

                combined = "\n".join(
                    part for part in [fortune, advice] if part
                )

                blocks.append(
                    f"[{item['rank']}]\n{combined}"
                )

            elif field == "lucky_place":
                lucky_place = normalize_text(item["lucky_place"])

                blocks.append(
                    f"[{item['rank']}]\n{lucky_place}"
                )

        source = "\n\n".join(blocks)

        print(
            f"[번역] {field} "
            f"{batch[0]['rank']}~{batch[-1]['rank']}위 번역 중..."
        )

        translated_text = translate_long_text(source)

        translated_batch = parse_numbered_translation(
            translated_text,
            len(batch)
        )

        # 번호별 번역 결과를 원래 순서에 맞게 저장
        for item, translated in zip(batch, translated_batch):
            index = items.index(item)

            if translated:
                results[index] = translated

        # 배치 전체가 제대로 파싱되지 않은 경우
        # 해당 3개만 개별 번역
        for item in batch:
            index = items.index(item)

            if results[index]:
                continue

            if field == "fortune":
                fortune = normalize_text(item["fortune"])
                advice = normalize_text(item["advice"])

                combined = "\n".join(
                    part for part in [fortune, advice] if part
                )

                if combined:
                    try:
                        print(
                            f"[개별 번역 재시도] "
                            f"{item['rank']}위 운세"
                        )

                        results[index] = translator.translate(
                            combined
                        ).strip()

                    except Exception as e:
                        print(
                            f"[개별 번역 실패] "
                            f"{item['rank']}위 운세: {e}"
                        )

            elif field == "lucky_place":
                lucky_place = normalize_text(item["lucky_place"])

                if lucky_place:
                    try:
                        print(
                            f"[개별 번역 재시도] "
                            f"{item['rank']}위 행운의 장소"
                        )

                        results[index] = translator.translate(
                            lucky_place
                        ).strip()

                    except Exception as e:
                        print(
                            f"[개별 번역 실패] "
                            f"{item['rank']}위 행운의 장소: {e}"
                        )

    return results


print("[번역 1/2] 운세/조언을 3개씩 묶어서 번역합니다.")

translated_fortunes = translate_in_batches(
    raw_items,
    "fortune",
    batch_size=3
)


print("[번역 2/2] 행운의 장소를 3개씩 묶어서 번역합니다.")

translated_lucky_places = translate_in_batches(
    raw_items,
    "lucky_place",
    batch_size=3
)


# 4. 번역 결과 적용
for index, item in enumerate(raw_items):

    translated_fortune = translated_fortunes[index]

    # 번역 결과가 없는 경우 원문 사용
    if not translated_fortune:
        translated_fortune = "\n".join(
            part for part in [
                item["fortune"],
                item["advice"]
            ]
            if part
        )

        print(
            f"[번역 결과 누락] "
            f"{item['sign']} 운세는 원문을 사용합니다."
        )

    translated_lucky_place = translated_lucky_places[index]

    # 행운의 장소 번역 결과가 없는 경우 원문 사용
    if not translated_lucky_place:
        translated_lucky_place = item["lucky_place"]

        print(
            f"[번역 결과 누락] "
            f"{item['sign']} 행운의 장소는 원문을 사용합니다."
        )

    ranking.append({
        "rank": item["rank"],
        "sign": item["sign"],
        "key": item["key"],
        "fortune": translated_fortune,
        "advice": "",
        "lucky_place": translated_lucky_place
    })


ranking.sort(key=lambda x: x["rank"])


# 5. 번역 결과 적용
for index, item in enumerate(raw_items):

    translated_fortune = translated_fortunes[index]

    # 번역 결과가 특정 번호에서 누락된 경우
    # 해당 별자리의 원문을 사용한다.
    if not translated_fortune:
        translated_fortune = "\n".join(
            part for part in [
                item["fortune"],
                item["advice"]
            ]
            if part
        )

        print(
            f"[번역 결과 누락] "
            f"{item['sign']} 운세는 원문을 사용합니다."
        )

    translated_lucky_place = translated_lucky_places[index]

    # 행운의 장소 번역 결과가 누락된 경우 원문 사용
    if not translated_lucky_place:
        translated_lucky_place = item["lucky_place"]

        print(
            f"[번역 결과 누락] "
            f"{item['sign']} 행운의 장소는 원문을 사용합니다."
        )

    ranking.append({
        "rank": item["rank"],
        "sign": item["sign"],
        "key": item["key"],
        "fortune": translated_fortune,
        "advice": "",
        "lucky_place": translated_lucky_place
    })


ranking.sort(key=lambda x: x["rank"])


# 6. 전체 순위 텍스트
top_text = [
    f"{item['rank']}위 {item['sign']}"
    for item in ranking
]

ranking_text = "\n".join(top_text)


# 7. 별자리별 데이터 생성
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


# 8. JSON 생성
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
