import re
import json
import sys
import urllib.request
import time
from html import unescape

CHANNELS = [
    # Украинские
    "ukrpravda_news",
    "DeepStateUA",
    "operativnoZSU",
    "amk_mapping",
    "uniannet",
    # Российские
    "rybar",
    "militarysummary",
    "readovkanews",
    "tass_agency",
    # Нейтральные / OSINT
    "UAWeapons",
    "Osinttechnical",
]

CHANNEL_COUNTRY = {
    "ukrpravda_news": "UA", "DeepStateUA": "UA", "operativnoZSU": "UA",
    "amk_mapping": "UA", "uniannet": "UA",
    "rybar": "RU", "militarysummary": "RU", "readovkanews": "RU", "tass_agency": "RU",
    "UAWeapons": "OSINT", "Osinttechnical": "OSINT",
}

# Расширенный словарь городов с координатами
CITY_COORDS = {
    # Украина
    "Киев": [50.4501, 30.5234], "Kyiv": [50.4501, 30.5234], "Києві": [50.4501, 30.5234], "Києва": [50.4501, 30.5234],
    "Харьков": [49.9935, 36.2304], "Kharkiv": [49.9935, 36.2304], "Харкові": [49.9935, 36.2304], "Харкова": [49.9935, 36.2304],
    "Одесса": [46.4775, 30.7326], "Odesa": [46.4775, 30.7326], "Одесі": [46.4775, 30.7326], "Одессы": [46.4775, 30.7326],
    "Донецк": [48.0159, 37.8029], "Donetsk": [48.0159, 37.8029], "Донецьк": [48.0159, 37.8029], "Донецка": [48.0159, 37.8029],
    "Луганск": [48.5740, 39.3078], "Luhansk": [48.5740, 39.3078],
    "Запорожье": [47.8388, 35.1396], "Zaporizhzhia": [47.8388, 35.1396], "Запоріжжі": [47.8388, 35.1396],
    "Херсон": [46.6354, 32.6169], "Kherson": [46.6354, 32.6169], "Херсоні": [46.6354, 32.6169],
    "Мариуполь": [47.0951, 37.5413], "Mariupol": [47.0951, 37.5413],
    "Бахмут": [48.5956, 38.0011], "Bakhmut": [48.5956, 38.0011],
    "Сумы": [50.9077, 34.7981], "Sumy": [50.9077, 34.7981], "Сумах": [50.9077, 34.7981],
    "Чернигов": [51.4982, 31.2893], "Chernihiv": [51.4982, 31.2893],
    "Днепр": [48.4647, 35.0462], "Dnipro": [48.4647, 35.0462], "Дніпрі": [48.4647, 35.0462],
    "Львов": [49.8397, 24.0297], "Lviv": [49.8397, 24.0297], "Львові": [49.8397, 24.0297],
    "Винница": [49.2331, 28.4682], "Vinnytsia": [49.2331, 28.4682],
    "Житомир": [50.2547, 28.6587], "Zhytomyr": [50.2547, 28.6587],
    "Полтава": [49.5883, 34.5514], "Poltava": [49.5883, 34.5514],
    "Черкассы": [49.4444, 32.0598], "Cherkasy": [49.4444, 32.0598],
    "Николаев": [46.9750, 31.9946], "Mykolaiv": [46.9750, 31.9946], "Миколаєві": [46.9750, 31.9946],
    "Кривой Рог": [47.9105, 33.3918], "Kryvyi Rih": [47.9105, 33.3918],
    "Славянск": [48.8531, 37.6182], "Sloviansk": [48.8531, 37.6182],
    "Краматорск": [48.7389, 37.5848], "Kramatorsk": [48.7389, 37.5848],
    "Авдеевка": [48.1397, 37.7464], "Avdiivka": [48.1397, 37.7464],
    "Покровск": [48.2825, 37.1761], "Pokrovsk": [48.2825, 37.1761],
    "Купянск": [49.7104, 37.6153], "Kupiansk": [49.7104, 37.6153],
    "Изюм": [49.2148, 37.2568], "Izium": [49.2148, 37.2568],
    "Лиман": [48.9875, 37.8057], "Lyman": [48.9875, 37.8057],
    "Соледар": [48.6870, 38.0744], "Soledar": [48.6870, 38.0744],
    "Торецк": [48.4017, 37.8478], "Toretsk": [48.4017, 37.8478],
    "Кременная": [49.0565, 38.2194], "Kreminna": [49.0565, 38.2194],
    "Северодонецк": [48.9487, 38.4924], "Sievierodonetsk": [48.9487, 38.4924],
    "Лисичанск": [48.9023, 38.4417], "Lysychansk": [48.9023, 38.4417],
    "Кривой Рог": [47.9105, 33.3918],
    "Мелитополь": [46.8489, 35.3654], "Melitopol": [46.8489, 35.3654],
    "Бердянск": [46.7573, 36.7885], "Berdiansk": [46.7573, 36.7885],
    "Ужгород": [48.6208, 22.2879], "Uzhhorod": [48.6208, 22.2879],
    "Ивано-Франковск": [48.9226, 24.7111],
    "Тернополь": [49.5535, 25.5948], "Ternopil": [49.5535, 25.5948],
    "Ровно": [50.6199, 26.2516], "Rivne": [50.6199, 26.2516],
    "Луцк": [50.7472, 25.3254], "Lutsk": [50.7472, 25.3254],
    "Хмельницкий": [49.4229, 26.9871], "Khmelnytskyi": [49.4229, 26.9871],
    "Черновцы": [48.2917, 25.9354], "Chernivtsi": [48.2917, 25.9354],
    "Кропивницкий": [48.5079, 32.2623],

    # Россия (приграничные и крупные)
    "Курск": [51.7304, 36.1926], "Kursk": [51.7304, 36.1926],
    "Белгород": [50.5952, 36.5873], "Belgorod": [50.5952, 36.5873],
    "Брянск": [53.2435, 34.3639], "Bryansk": [53.2435, 34.3639],
    "Воронеж": [51.6720, 39.1843], "Voronezh": [51.6720, 39.1843],
    "Ростов": [47.2225, 39.7188], "Ростов-на-Дону": [47.2225, 39.7188], "Rostov": [47.2225, 39.7188],
    "Москва": [55.7558, 37.6173], "Moscow": [55.7558, 37.6173],
    "Краснодар": [45.0355, 38.9753], "Krasnodar": [45.0355, 38.9753],
    "Смоленск": [54.7826, 32.0453], "Smolensk": [54.7826, 32.0453],
    "Тула": [54.1961, 37.6182], "Tula": [54.1961, 37.6182],
    "Крым": [45.3453, 34.4997], "Симферополь": [44.9521, 34.1024], "Simferopol": [44.9521, 34.1024],
    "Севастополь": [44.6166, 33.5254], "Sevastopol": [44.6166, 33.5254],
    "Керчь": [45.3531, 36.4744], "Kerch": [45.3531, 36.4744],
    "Джанкой": [45.7093, 34.3885],
}

# Города, которые однозначно на территории Украины (для определения страны)
UA_CITIES = {"Киев","Kyiv","Києві","Києва","Харьков","Kharkiv","Харкові","Харкова","Одесса","Odesa","Одесі","Одессы",
             "Донецк","Donetsk","Донецьк","Донецка","Луганск","Luhansk","Запорожье","Zaporizhzhia","Запоріжжі",
             "Херсон","Kherson","Херсоні","Мариуполь","Mariupol","Бахмут","Bakhmut","Сумы","Sumy","Сумах",
             "Чернигов","Chernihiv","Днепр","Dnipro","Дніпрі","Львов","Lviv","Львові","Винница","Vinnytsia",
             "Житомир","Zhytomyr","Полтава","Poltava","Черкассы","Cherkasy","Николаев","Mykolaiv","Миколаєві",
             "Кривой Рог","Kryvyi Rih","Славянск","Sloviansk","Краматорск","Kramatorsk","Авдеевка","Avdiivka",
             "Покровск","Pokrovsk","Купянск","Kupiansk","Изюм","Izium","Лиман","Lyman","Соледар","Soledar",
             "Торецк","Toretsk","Кременная","Kreminna","Северодонецк","Sievierodonetsk","Лисичанск","Lysychansk",
             "Мелитополь","Melitopol","Бердянск","Berdiansk","Ужгород","Uzhhorod","Ивано-Франковск",
             "Тернополь","Ternopil","Ровно","Rivne","Луцк","Lutsk","Хмельницкий","Khmelnytskyi",
             "Черновцы","Chernivtsi","Кропивницкий"}

RU_CITIES = {"Курск","Kursk","Белгород","Belgorod","Брянск","Bryansk","Воронеж","Voronezh",
             "Ростов","Ростов-на-Дону","Rostov","Москва","Moscow","Краснодар","Krasnodar",
             "Смоленск","Smolensk","Тула","Tula","Крым","Симферополь","Simferopol","Севастополь",
             "Sevastopol","Керчь","Kerch","Джанкой"}


def fetch_channel(channel):
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  Ошибка загрузки @{channel}: {e}", file=sys.stderr)
        return ""


def extract_posts(html):
    posts = []
    blocks = re.split(r'<div class="tgme_widget_message_wrap[^"]*"', html)
    for block in blocks[1:]:
        date_match = re.search(r'<time datetime="([^"]+)"', block)
        date_str = date_match.group(1) if date_match else ""

        text_match = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*</div>',
            block, re.DOTALL
        )
        if not text_match:
            continue
        text = text_match.group(1)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = unescape(text).strip()

        id_match = re.search(r'data-post="([^"]+)"', block)
        url = f"https://t.me/{id_match.group(1)}" if id_match else ""

        if len(text) > 20:
            posts.append({"text": text, "date": date_str, "url": url})
    return posts


def find_best_city(text):
    """Ищет ВСЕ упоминания городов, возвращает тот, что ближе всего к началу текста
    (обычно главная новость — в первом абзаце)."""
    tl = text.lower()
    found = []
    for city, coords in CITY_COORDS.items():
        idx = tl.find(city.lower())
        if idx >= 0:
            found.append((idx, city, coords))
    if not found:
        return None, None
    # Сортируем по позиции в тексте, берём самый ранний
    found.sort(key=lambda x: x[0])
    return found[0][2], found[0][1]


def country_by_city(city):
    """Определяет страну по названию города."""
    if city in UA_CITIES:
        return "UA"
    if city in RU_CITIES:
        return "RU"
    return "OSINT"


def classify_event(text):
    tl = text.lower()
    if any(w in tl for w in ["тревога", "alert", "сирена", "тривога", "воздушная"]):
        return "Air Raid Alert"
    if any(w in tl for w in ["удар", "strike", "взрыв", "explosion", "прилёт", "приліт", "обстр"]):
        return "Military Strike"
    if any(w in tl for w in ["наступление", "offensive", "атака", "attack", "наступ", "прорыв"]):
        return "Military Offensive"
    if any(w in tl for w in ["бои", "battle", "fight", "бой", "бій", "боях"]):
        return "Military Operation"
    return "Security Incident"


def make_dedup_key(ev):
    """Ключ дедупликации: (округлённые координаты, тип, час)."""
    # Округляем координаты до 0.2° — это ~20 км
    lat_r = round(ev["lat"] * 5) / 5
    lng_r = round(ev["lng"] * 5) / 5
    hour = ""
    if ev.get("date"):
        try:
            hour = ev["date"][:13]  # YYYY-MM-DDTHH
        except:
            hour = ""
    return f"{lat_r},{lng_r}|{ev['event_type']}|{hour}"


def main():
    all_events = []
    seen_texts = set()
    seen_dedup = set()
    duplicates = 0

    for channel in CHANNELS:
        print(f"Парсим @{channel}...")
        html = fetch_channel(channel)
        if not html:
            continue
        posts = extract_posts(html)
        print(f"  Найдено постов: {len(posts)}")
        matched = 0

        for post in posts:
            text = post["text"]
            key = text[:80]
            if key in seen_texts:
                continue
            seen_texts.add(key)

            coords, city = find_best_city(text)
            if not coords:
                continue
            matched += 1

            ev = {
                "id": len(all_events) + 1,
                "url": post["url"] or f"https://t.me/s/{channel}",
                "date": post["date"],
                "event_type": classify_event(text),
                "location": city,
                "country": country_by_city(city),
                "lat": coords[0],
                "lng": coords[1],
                "confidence": "MEDIUM",
                "description": text[:200],
                "channel": channel,
            }

            dedup = make_dedup_key(ev)
            if dedup in seen_dedup:
                duplicates += 1
                continue
            seen_dedup.add(dedup)

            all_events.append(ev)

        print(f"  Совпало с городами: {matched}")
        time.sleep(1)

    output = "window.TG_DATA = " + json.dumps({"events": all_events}, ensure_ascii=False) + ";"
    with open("data/telegram-events.js", "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✅ Итого: {len(all_events)} событий (отброшено дубликатов: {duplicates})")
    print(f"   → data/telegram-events.js")


if __name__ == "__main__":
    main()
