import re
import json
import sys
import urllib.request
import time
from html import unescape

CHANNELS = [
    # Украинские официальные
    "kpszsu",
    "GeneralStaffZSU",
    "operativnoZSU",
    # Украинские новостные
    "ukrpravda_news",
    "uniannet",
    # Украинские OSINT
    "DeepStateUA",
    "amk_mapping",
    "OsintFlow",
    "ukraine_observer",
    # Российские официальные / военкоры
    "rybar",
    "voenkorKotenok",
    "wargonzo",
    "dva_majors",
    "readovkanews",
    "tass_agency",
    # Российские OSINT
    "militarysummary",
    "lost_armour",
    # Независимые / международные
    "UAWeapons",
    "Osinttechnical",
    "informnapalm",
    # Каналы воздушных тревог (Украина)
    "AerisRimor",
    "monitoringwar",
    # Каналы воздушных тревог (Россия)
    "sputnikrussia_radar",
    "radar_rf",
    "locatorru",
    "ruporruss",
    "grohot_pgr",
    "russiamonitoring_radar_bpla",
]

CHANNEL_COUNTRY = {
    # Украинские
    "kpszsu": "UA", "GeneralStaffZSU": "UA", "operativnoZSU": "UA",
    "ukrpravda_news": "UA", "uniannet": "UA", "DeepStateUA": "UA",
    "amk_mapping": "UA", "OsintFlow": "UA", "ukraine_observer": "UA",
    # Российские
    "rybar": "RU", "voenkorKotenok": "RU", "wargonzo": "RU",
    "dva_majors": "RU", "readovkanews": "RU", "tass_agency": "RU",
    "militarysummary": "RU", "lost_armour": "RU",
    # Независимые / OSINT
    "UAWeapons": "OSINT", "Osinttechnical": "OSINT", "informnapalm": "OSINT",
    # Каналы тревог
    "AerisRimor": "UA", "monitoringwar": "UA",
    "sputnikrussia_radar": "RU", "radar_rf": "RU", "locatorru": "RU",
    "ruporruss": "RU", "grohot_pgr": "RU", "russiamonitoring_radar_bpla": "RU",
}

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
    "Павлоград": [48.5204, 35.8700],
    "Каменское": [48.5111, 34.6167],
    "Никополь": [47.5667, 34.4000],
    "Умань": [48.7484, 30.2219],
    "Белая Церковь": [49.7950, 30.1167],
    "Бровары": [50.5111, 30.7900],
    "Ирпень": [50.5218, 30.2506],
    "Буча": [50.5431, 30.2117],
    "Вышгород": [50.5841, 30.4901],
    "Фастов": [50.0747, 29.9181],

    # Россия — крупные города
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
    "Орел": [52.9651, 36.0785], "Oryol": [52.9651, 36.0785],
    "Липецк": [52.6031, 39.5708], "Lipetsk": [52.6031, 39.5708],
    "Тамбов": [52.7212, 41.4523], "Tambov": [52.7212, 41.4523],
    "Калуга": [54.5138, 36.2612], "Kaluga": [54.5138, 36.2612],
    "Тверь": [56.8587, 35.9176], "Tver": [56.8587, 35.9176],
    "Новгород": [58.5215, 31.2755], "Novgorod": [58.5215, 31.2755],
    "Псков": [57.8194, 28.3318], "Pskov": [57.8194, 28.3318],
    "Сочи": [43.5855, 39.7231], "Sochi": [43.5855, 39.7231],
    "Анапа": [44.8909, 37.3198], "Anapa": [44.8909, 37.3198],
    "Новороссийск": [44.7239, 37.7686], "Novorossiysk": [44.7239, 37.7686],
    "Таганрог": [47.2097, 38.9353], "Taganrog": [47.2097, 38.9353],
    # Россия — областные центры и приграничные
    "Валуйки": [50.2086, 38.1016], "Valuyki": [50.2086, 38.1016],
    "Шебекино": [50.4067, 36.8925], "Shebekino": [50.4067, 36.8925],
    "Грайворон": [50.4828, 35.6628],
    "Суджа": [51.1974, 35.2720], "Sudzha": [51.1974, 35.2720],
    "Рыльск": [51.5697, 34.6823],
    "Клинцы": [52.7561, 32.2347],
    "Новозыбков": [52.5370, 31.9344],
    "Курчатов": [51.6600, 35.6500],
    "Железногорск": [52.3319, 35.3707],
    "Ливны": [52.4245, 37.5997],
    "Мценск": [53.2813, 36.5733],
    "Волгоград": [48.7080, 44.5133], "Volgograd": [48.7080, 44.5133],
    "Астрахань": [46.3497, 48.0408], "Astrakhan": [46.3497, 48.0408],
    "Саратов": [51.5336, 46.0343], "Saratov": [51.5336, 46.0343],
    "Энгельс": [51.5000, 46.1167],
    "Балашов": [51.5512, 43.1768],
    "Пенза": [53.2007, 45.0046], "Penza": [53.2007, 45.0046],
    "Самара": [53.1959, 50.1061], "Samara": [53.1959, 50.1061],
    "Ульяновск": [54.3142, 48.4031], "Ulyanovsk": [54.3142, 48.4031],
    "Казань": [55.8304, 49.0661], "Kazan": [55.8304, 49.0661],
    "Нижний Новгород": [56.3269, 44.0059],
    "Челябинск": [55.1644, 61.4368], "Chelyabinsk": [55.1644, 61.4368],
    "Екатеринбург": [56.8389, 60.6057], "Yekaterinburg": [56.8389, 60.6057],
    "Новосибирск": [55.0084, 82.9357], "Novosibirsk": [55.0084, 82.9357],
    "Омск": [54.9885, 73.3242], "Omsk": [54.9885, 73.3242],
    "Тюмень": [57.1522, 65.5272], "Tyumen": [57.1522, 65.5272],
    "Пермь": [58.0105, 56.2502], "Perm": [58.0105, 56.2502],
    "Уфа": [54.7388, 55.9721], "Ufa": [54.7388, 55.9721],
    "Ижевск": [56.8527, 53.2115], "Izhevsk": [56.8527, 53.2115],
    "Оренбург": [51.7727, 55.0988], "Orenburg": [51.7727, 55.0988],
    "Санкт-Петербург": [59.9311, 30.3609], "Питер": [59.9311, 30.3609],
    "Мурманск": [68.9585, 33.0827], "Murmansk": [68.9585, 33.0827],
    "Архангельск": [64.5393, 40.5182],
    "Петрозаводск": [61.7849, 34.3469],
    "Вологда": [59.2205, 39.8915],
    "Ярославль": [57.6261, 39.8845],
    "Кострома": [57.7665, 40.9269],
    "Владимир": [56.1290, 40.4070],
    "Рязань": [54.6269, 39.6916], "Ryazan": [54.6269, 39.6916],
    "Краснодарский": [45.0355, 38.9753],
}

UA_CITIES = {
    "Киев","Kyiv","Києві","Києва","Харьков","Kharkiv","Харкові","Харкова","Одесса","Odesa","Одесі","Одессы",
    "Донецк","Donetsk","Донецьк","Донецка","Луганск","Luhansk","Запорожье","Zaporizhzhia","Запоріжжі",
    "Херсон","Kherson","Херсоні","Мариуполь","Mariupol","Бахмут","Bakhmut","Сумы","Sumy","Сумах",
    "Чернигов","Chernihiv","Днепр","Dnipro","Дніпрі","Львов","Lviv","Львові","Винница","Vinnytsia",
    "Житомир","Zhytomyr","Полтава","Poltava","Черкассы","Cherkasy","Николаев","Mykolaiv","Миколаєві",
    "Кривой Рог","Kryvyi Rih","Славянск","Sloviansk","Краматорск","Kramatorsk","Авдеевка","Avdiivka",
    "Покровск","Pokrovsk","Купянск","Kupiansk","Изюм","Izium","Лиман","Lyman","Соледар","Soledar",
    "Торецк","Toretsk","Кременная","Kreminna","Северодонецк","Sievierodonetsk","Лисичанск","Lysychansk",
    "Мелитополь","Melitopol","Бердянск","Berdiansk","Ужгород","Uzhhorod","Ивано-Франковск",
    "Тернополь","Ternopil","Ровно","Rivne","Луцк","Lutsk","Хмельницкий","Khmelnytskyi",
    "Черновцы","Chernivtsi","Кропивницкий","Павлоград","Каменское","Никополь","Умань",
    "Белая Церковь","Бровары","Ирпень","Буча","Вышгород","Фастов"
}

RU_CITIES = {
    "Курск","Kursk","Белгород","Belgorod","Брянск","Bryansk","Воронеж","Voronezh",
    "Ростов","Ростов-на-Дону","Rostov","Москва","Moscow","Краснодар","Krasnodar",
    "Смоленск","Smolensk","Тула","Tula","Крым","Симферополь","Simferopol","Севастополь",
    "Sevastopol","Керчь","Kerch","Джанкой","Орел","Oryol","Липецк","Lipetsk",
    "Тамбов","Tambov","Калуга","Kaluga","Тверь","Tver","Новгород","Novgorod",
    "Псков","Pskov","Сочи","Sochi","Анапа","Anapa","Новороссийск","Novorossiysk",
    "Таганрог","Taganrog","Валуйки","Valuyki","Шебекино","Shebekino","Грайворон",
    "Суджа","Sudzha","Рыльск","Клинцы","Новозыбков","Курчатов","Железногорск",
    "Ливны","Мценск","Волгоград","Volgograd","Астрахань","Astrakhan","Саратов","Saratov",
    "Энгельс","Балашов","Пенза","Penza","Самара","Samara","Ульяновск","Ulyanovsk",
    "Казань","Kazan","Нижний Новгород","Челябинск","Chelyabinsk","Екатеринбург","Yekaterinburg",
    "Новосибирск","Novosibirsk","Омск","Omsk","Тюмень","Tyumen","Пермь","Perm",
    "Уфа","Ufa","Ижевск","Izhevsk","Оренбург","Orenburg","Санкт-Петербург","Питер",
    "Мурманск","Murmansk","Архангельск","Петрозаводск","Вологда","Ярославль",
    "Кострома","Владимир","Рязань","Ryazan"
}


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
    tl = text.lower()
    found = []
    for city, coords in CITY_COORDS.items():
        idx = tl.find(city.lower())
        if idx >= 0:
            found.append((idx, city, coords))
    if not found:
        return None, None
    found.sort(key=lambda x: x[0])
    return found[0][2], found[0][1]


def country_by_city(city):
    if city in UA_CITIES:
        return "UA"
    if city in RU_CITIES:
        return "RU"
    return "OSINT"


def classify_event(text):
    tl = text.lower()
    if any(w in tl for w in ["тревога", "alert", "сирена", "тривога", "воздушная", "повітряна", "опасность", "угроза", "бпла"]):
        return "Air Raid Alert"
    if any(w in tl for w in ["удар", "strike", "взрыв", "explosion", "прилёт", "приліт", "обстр", "дрон", "ракет", "пво"]):
        return "Military Strike"
    if any(w in tl for w in ["наступление", "offensive", "атака", "attack", "наступ", "прорыв", "штурм"]):
        return "Military Offensive"
    if any(w in tl for w in ["бои", "battle", "fight", "бой", "бій", "боях", "позиции"]):
        return "Military Operation"
    return "Security Incident"


def make_dedup_key(ev):
    if ev.get("url"):
        return ev["url"]
    return ev["channel"] + "|" + ev.get("description", "")[:80]


def main():
    all_events = []
    seen_texts = set()
    seen_dedup = set()
    duplicates = 0
    stats = {}

    for channel in CHANNELS:
        print(f"Парсим @{channel}...")
        html = fetch_channel(channel)
        if not html:
            stats[channel] = 0
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

        stats[channel] = matched
        print(f"  Совпало с городами: {matched}")
        time.sleep(1)

    output = "window.TG_DATA = " + json.dumps({"events": all_events}, ensure_ascii=False) + ";"
    with open("data/telegram-events.js", "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✅ Итого: {len(all_events)} событий (отброшено дубликатов: {duplicates})")

    print("\n📊 Статистика по каналам:")
    for ch, count in sorted(stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  @{ch}: {count}")


if __name__ == "__main__":
    main()
