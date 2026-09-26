import re
import json
import sys
import urllib.request
import time
import random
import math
import os
from html import unescape
from collections import Counter

CHANNELS = [
    "kpszsu", "GeneralStaffZSU", "operativnoZSU",
    "ukrpravda_news", "uniannet",
    "DeepStateUA", "amk_mapping", "OsintFlow", "ukraine_observer",
    "rybar", "voenkorKotenok", "wargonzo", "dva_majors", "readovkanews", "tass_agency",
    "militarysummary", "lost_armour",
    "UAWeapons", "Osinttechnical", "informnapalm",
    "AerisRimor", "monitoringwar",
    "sputnikrussia_radar", "radar_rf", "locatorru",
    "ruporruss", "grohot_pgr",
]

CHANNEL_COUNTRY = {
    "kpszsu": "UA", "GeneralStaffZSU": "UA", "operativnoZSU": "UA",
    "ukrpravda_news": "UA", "uniannet": "UA", "DeepStateUA": "UA",
    "amk_mapping": "UA", "OsintFlow": "UA", "ukraine_observer": "UA",
    "AerisRimor": "UA", "monitoringwar": "UA",
    "rybar": "RU", "voenkorKotenok": "RU", "wargonzo": "RU",
    "dva_majors": "RU", "readovkanews": "RU", "tass_agency": "RU",
    "militarysummary": "RU", "lost_armour": "RU",
    "sputnikrussia_radar": "RU", "radar_rf": "RU", "locatorru": "RU",
    "ruporruss": "RU", "grohot_pgr": "RU",
    "UAWeapons": "OSINT", "Osinttechnical": "OSINT", "informnapalm": "OSINT",
}

# Алиасы: украинские и другие написания → каноническое название (RU)
# Ключ — корень, ищется как подстрока в тексте
TRANSLIT_ALIASES = {
    # Украинские названия российских городов
    "ульяновськ": [54.3142, 48.4031, "Ульяновск", "RU"],
    "вороніж": [51.6720, 39.1843, "Воронеж", "RU"],
    "воронез": [51.6720, 39.1843, "Воронеж", "RU"],
    "курськ": [51.7304, 36.1926, "Курск", "RU"],
    "бєлгород": [50.5952, 36.5873, "Белгород", "RU"],
    "брянськ": [53.2435, 34.3639, "Брянск", "RU"],
    "орєл": [52.9651, 36.0785, "Орел", "RU"],
    "липецьк": [52.6031, 39.5708, "Липецк", "RU"],
    "тамбов": [52.7212, 41.4523, "Тамбов", "RU"],
    "смоленськ": [54.7826, 32.0453, "Смоленск", "RU"],
    "твер": [56.8587, 35.9176, "Тверь", "RU"],
    "псков": [57.8194, 28.3318, "Псков", "RU"],
    "новгород": [58.5215, 31.2755, "Новгород", "RU"],
    "мурманськ": [68.9585, 33.0827, "Мурманск", "RU"],
    "архангельськ": [64.5393, 40.5182, "Архангельск", "RU"],
    "астрахан": [46.3497, 48.0408, "Астрахань", "RU"],
    "челябінськ": [55.1644, 61.4368, "Челябинск", "RU"],
    "єкатеринбург": [56.8389, 60.6057, "Екатеринбург", "RU"],
    "омськ": [54.9885, 73.3242, "Омск", "RU"],
    "новосибірськ": [55.0084, 82.9357, "Новосибирск", "RU"],
    "іркутськ": [52.2871, 104.3051, "Иркутск", "RU"],
    "хабаровськ": [48.4827, 135.0838, "Хабаровск", "RU"],
    "волгоград": [48.7080, 44.5133, "Волгоград", "RU"],
    "саратов": [51.5336, 46.0343, "Саратов", "RU"],
    "самар": [53.1959, 50.1061, "Самара", "RU"],
    "казан": [55.8304, 49.0661, "Казань", "RU"],
    "нижній новгород": [56.3269, 44.0059, "Нижний Новгород", "RU"],
    "тула": [54.1961, 37.6182, "Тула", "RU"],
    "калуг": [54.5138, 36.2612, "Калуга", "RU"],
    "рязан": [54.6269, 39.6916, "Рязань", "RU"],
    "пенз": [53.2007, 45.0046, "Пенза", "RU"],
    "оренбург": [51.7727, 55.0988, "Оренбург", "RU"],
    "тюмен": [57.1522, 65.5272, "Тюмень", "RU"],
    "кемеров": [55.3547, 86.0873, "Кемерово", "RU"],

    # Украинские названия областей РФ
    "ульяновська област": [54.3142, 48.4031, "Ульяновск", "RU"],
    "ульяновської област": [54.3142, 48.4031, "Ульяновск", "RU"],
    "воронезька област": [51.6720, 39.1843, "Воронеж", "RU"],
    "воронезької област": [51.6720, 39.1843, "Воронеж", "RU"],
    "курська област": [51.7304, 36.1926, "Курск", "RU"],
    "курської област": [51.7304, 36.1926, "Курск", "RU"],
    "бєлгородська област": [50.5952, 36.5873, "Белгород", "RU"],
    "бєлгородської област": [50.5952, 36.5873, "Белгород", "RU"],
    "брянська област": [53.2435, 34.3639, "Брянск", "RU"],
    "орловська област": [52.9651, 36.0785, "Орел", "RU"],
    "липецька област": [52.6031, 39.5708, "Липецк", "RU"],
    "тамбовська област": [52.7212, 41.4523, "Тамбов", "RU"],
    "ростовська област": [47.2225, 39.7188, "Ростов", "RU"],
    "ростовської област": [47.2225, 39.7188, "Ростов", "RU"],
    "краснодарський край": [45.0355, 38.9753, "Краснодар", "RU"],
    "волгоградська област": [48.7080, 44.5133, "Волгоград", "RU"],
    "саратовська област": [51.5336, 46.0343, "Саратов", "RU"],
    "самарська област": [53.1959, 50.1061, "Самара", "RU"],
    "пензенська област": [53.2007, 45.0046, "Пенза", "RU"],
    "нижньогородська област": [56.3269, 44.0059, "Нижний Новгород", "RU"],
    "оренбурзька област": [51.7727, 55.0988, "Оренбург", "RU"],
    "челябінська област": [55.1644, 61.4368, "Челябинск", "RU"],
    "свердловська област": [56.8389, 60.6057, "Екатеринбург", "RU"],
    "тюменська област": [57.1522, 65.5272, "Тюмень", "RU"],
    "омська област": [54.9885, 73.3242, "Омск", "RU"],
    "новосибірська област": [55.0084, 82.9357, "Новосибирск", "RU"],
    "кемеровська област": [55.3547, 86.0873, "Кемерово", "RU"],
    "іркутська област": [52.2871, 104.3051, "Иркутск", "RU"],
    "приморський край": [43.1155, 131.8855, "Владивосток", "RU"],
    "хабаровський край": [48.4827, 135.0838, "Хабаровск", "RU"],

    # Российские названия украинских областей
    "киевская област": [50.4501, 30.5234, "Киев", "UA"],
    "київська област": [50.4501, 30.5234, "Киев", "UA"],
    "львовская област": [49.8397, 24.0297, "Львов", "UA"],
    "львівська област": [49.8397, 24.0297, "Львов", "UA"],
    "одесская област": [46.4775, 30.7326, "Одесса", "UA"],
    "одеська област": [46.4775, 30.7326, "Одесса", "UA"],
    "харьковская област": [49.9935, 36.2304, "Харьков", "UA"],
    "харківська област": [49.9935, 36.2304, "Харьков", "UA"],
    "донецкая област": [48.0159, 37.8029, "Донецк", "UA"],
    "донецька област": [48.0159, 37.8029, "Донецк", "UA"],
    "луганская област": [48.5740, 39.3078, "Луганск", "UA"],
    "луганська област": [48.5740, 39.3078, "Луганск", "UA"],
    "запорожская област": [47.8388, 35.1396, "Запорожье", "UA"],
    "запорізька област": [47.8388, 35.1396, "Запорожье", "UA"],
    "херсонская област": [46.6354, 32.6169, "Херсон", "UA"],
    "херсонська област": [46.6354, 32.6169, "Херсон", "UA"],
    "николаевская област": [46.9750, 31.9946, "Николаев", "UA"],
    "миколаївська област": [46.9750, 31.9946, "Николаев", "UA"],
    "днепропетровская област": [48.4647, 35.0462, "Днепр", "UA"],
    "дніпропетровська област": [48.4647, 35.0462, "Днепр", "UA"],
    "полтавская област": [49.5883, 34.5514, "Полтава", "UA"],
    "полтавська област": [49.5883, 34.5514, "Полтава", "UA"],
    "сумская област": [50.9077, 34.7981, "Сумы", "UA"],
    "сумська област": [50.9077, 34.7981, "Сумы", "UA"],
    "черниговская област": [51.4982, 31.2893, "Чернигов", "UA"],
    "чернігівська област": [51.4982, 31.2893, "Чернигов", "UA"],
    "житомирская област": [50.2547, 28.6587, "Житомир", "UA"],
    "житомирська област": [50.2547, 28.6587, "Житомир", "UA"],
    "винницкая област": [49.2331, 28.4682, "Винница", "UA"],
    "вінницька област": [49.2331, 28.4682, "Винница", "UA"],
    "кировоградская област": [48.5079, 32.2623, "Кропивницкий", "UA"],
    "кіровоградська област": [48.5079, 32.2623, "Кропивницкий", "UA"],
    "черкасская област": [49.4444, 32.0598, "Черкассы", "UA"],
    "черкаська област": [49.4444, 32.0598, "Черкассы", "UA"],
    "ровенская област": [50.6199, 26.2516, "Ровно", "UA"],
    "рівненська област": [50.6199, 26.2516, "Ровно", "UA"],
    "волынская област": [50.7472, 25.3254, "Луцк", "UA"],
    "волинська област": [50.7472, 25.3254, "Луцк", "UA"],
    "тернопольская област": [49.5535, 25.5948, "Тернополь", "UA"],
    "тернопільська област": [49.5535, 25.5948, "Тернополь", "UA"],
    "хмельницкая област": [49.4229, 26.9871, "Хмельницкий", "UA"],
    "хмельницька област": [49.4229, 26.9871, "Хмельницкий", "UA"],
    "ивано-франковская област": [48.9226, 24.7111, "Ивано-Франковск", "UA"],
    "івано-франківська област": [48.9226, 24.7111, "Ивано-Франковск", "UA"],
    "закарпатская област": [48.6208, 22.2879, "Ужгород", "UA"],
    "закарпатська област": [48.6208, 22.2879, "Ужгород", "UA"],
    "черновицкая област": [48.2917, 25.9354, "Черновцы", "UA"],
    "чернівецька област": [48.2917, 25.9354, "Черновцы", "UA"],
}

EVENT_CONTEXT = ["удар", "обстр", "тревог", "взрыв", "прилёт", "приліт", "атак",
                 "бой", "наступлен", "наступ", "штурм", "бпла", "дрон", "ракет",
                 "пво", "по ", "в ", "на ", "оборон", "уразили", "уражено"]

STRONG_EVENT_WORDS = ["удар", "обстр", "тревог", "взрыв", "прилёт", "приліт",
                      "бпла", "дрон", "ракет", "пво", "штурм", "уразили", "уражено"]

DIRECT_VERB_PATTERNS = [
    r'ударил[аи]?\s+по\s+',
    r'ударил[аи]?\s+',
    r'атаковал[аи]?',
    r'обстрелял[аи]?',
    r'нанесли\s+удар\s+по',
    r'наносят\s+удары\s+по',
    r'уразили',
    r'поразили',
]

CONTINUATION_WORDS = ["также", "помимо", "кроме того", "кроме этого",
                      "наряду", "продолжила", "продолжили", "продолжает",
                      "продолжают", "параллельно", "одновременно",
                      "в то же время", "помимо этого"]

NOISE_CONTEXT = ["заяв", "сообщ", "минобороны",
                 "по данным", "по словам", "отметил", "подчеркн",
                 "написал", "передаёт", "передает", "цитирует",
                 "комментар", "пресс-служб"]

CANCEL_WORDS = ["отбой", "отменена", "отменён", "отменен",
                "завершена", "завершён", "завершен",
                "прекращена", "прекращён", "прекращен",
                "окончена", "угроза миновала", "опасность миновала"]

ALERT_WORDS = ["тревог", "опасност", "угроз", "alert", "бпла", "ракет"]

MILITARY_TERMS = ["рлс", "зрк", "с-300", "с-400", "с-500", "бук ", "панцирь",
                  "тор ", "тюльпан", "град ", "ураган", "смерч",
                  "искандер", "кинжал", "калибр", "шахед", "герань",
                  "ланцет", "точка-у", "тос-", "оса ", "стрела",
                  "шилка", "тунгуска", "радиолокацион", "комплекс", "установк"]

STOP_SETTLEMENTS = {
    "безопасное", "красное", "мирное", "новое", "тихое", "ясное",
    "победа", "дружба", "правда", "восток", "запад", "север", "юг",
    "искра", "заря", "маяк", "свобода", "россия", "украина",
    "северный", "южный", "западный", "восточный", "центральное",
    "новый", "старый", "малый", "большой", "верхний", "нижний",
    "дальний", "ближний", "дальнее", "ближнее", "веселое", "весёлое",
    "радостное", "светлое", "теплое", "тёплое", "глубокое",
    "широкое", "высокое", "низкое", "голубое", "синее",
    "зорька", "звезда", "солнце", "луна", "небо",
    "граница", "граничное", "пограничное", "приморское",
    "лесное", "степное", "речное", "озерное", "горное",
    "зеленое", "зелёное", "белое", "черное", "чёрное",
    "терек", "бук", "тор", "оса", "стрела", "искандер", "кинжал",
    "калибр", "шахед", "герань", "ланцет", "панцирь", "тюльпан",
    "град", "ураган", "смерч", "тунгуска", "шилка", "с-300", "с-400",
    "точка", "печора", "акация", "гиацинт", "пион",
}

SETTLEMENTS_BY_NAME = {}


def load_settlements():
    global SETTLEMENTS_BY_NAME
    path = 'data/settlements.js'
    if not os.path.exists(path):
        print("  ⚠️ data/settlements.js не найден", file=sys.stderr)
        return
    print("Загружаю базу населённых пунктов...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('window.SETTLEMENTS = ', '').rstrip(';').rstrip()
    data = json.loads(json_str)
    skipped = 0
    for s in data:
        name_low = s['name'].lower()
        if name_low in STOP_SETTLEMENTS:
            skipped += 1
            continue
        SETTLEMENTS_BY_NAME.setdefault(name_low, []).append(
            (s['lat'], s['lng'], s['country'], s['name'], s.get('population', 0))
        )
    print(f"  Загружено {len(data)} записей, пропущено стоп-названий: {skipped}")


def fetch_channel(channel):
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
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


def find_alias(text):
    """Ищет украинские (и другие) транслитерации городов/областей РФ и UA."""
    tl = text.lower()
    # Ключи сортируем по длине — длинные первыми
    for key in sorted(TRANSLIT_ALIASES.keys(), key=lambda k: -len(k)):
        if key in tl:
            coords = TRANSLIT_ALIASES[key]
            return (coords[0], coords[1]), coords[2], coords[3]
    return None, None, None


def is_military_term_context(text, phrase):
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    before = tl[max(0, idx-30):idx]
    after = tl[idx+len(phrase):idx+len(phrase)+30]
    for term in MILITARY_TERMS:
        if term in before or term in after:
            return True
    if ('«' in before[-3:] or '“' in before[-3:]) and ('»' in after[:3] or '”' in after[:3]):
        return True
    return False


def has_strong_event_nearby(text, city_name):
    tl = text.lower()
    city_low = city_name.lower()
    idx = tl.find(city_low)
    if idx < 0:
        return False
    window = tl[max(0, idx-80):idx+len(city_low)+80]
    for w in STRONG_EVENT_WORDS:
        if w in window:
            return True
    return False


def has_direct_verb_before(text, city_name):
    tl = text.lower()
    idx = tl.find(city_name.lower())
    if idx < 0:
        return False
    before = tl[max(0, idx-50):idx]
    for pat in DIRECT_VERB_PATTERNS:
        if re.search(pat, before):
            return True
    return False


def has_continuation_before(text, city_name):
    tl = text.lower()
    idx = tl.find(city_name.lower())
    if idx < 0:
        return False
    before = tl[max(0, idx-40):idx]
    for w in CONTINUATION_WORDS:
        if w in before:
            return True
    return False


def find_best_city(text, channel_country):
    if not SETTLEMENTS_BY_NAME:
        return None, None

    tl = text.lower()
    words = re.findall(r'[а-яёa-z0-9\-]+', tl)
    if not words:
        return None, None

    candidates = []
    N = len(words)

    for size in (3, 2, 1):
        for i in range(N - size + 1):
            phrase = ' '.join(words[i:i+size])
            if phrase not in SETTLEMENTS_BY_NAME:
                continue
            if is_military_term_context(text, phrase):
                continue

            coords_list = SETTLEMENTS_BY_NAME[phrase]
            if channel_country in ("UA", "RU"):
                filtered = [c for c in coords_list if c[2] == channel_country]
                if not filtered:
                    continue
                best = max(filtered, key=lambda x: x[4])
            else:
                best = max(coords_list, key=lambda x: x[4])

            lat, lng, country, orig, population = best

            if not has_strong_event_nearby(text, phrase):
                continue

            pos_in_text = tl.find(phrase)
            if pos_in_text < 0:
                pos_in_text = 0
            before = tl[max(0, pos_in_text-60):pos_in_text]
            after = tl[pos_in_text+len(phrase):pos_in_text+len(phrase)+60]

            score = 0

            if has_direct_verb_before(text, phrase):
                score += 30
            if pos_in_text < 150:
                score += 20
            if has_continuation_before(text, phrase):
                score -= 25

            for w in NOISE_CONTEXT:
                if w in before:
                    score -= 15
                    break

            event_hits = 0
            for w in EVENT_CONTEXT:
                if w in before or w in after:
                    event_hits += 1
            score += event_hits * 8

            if population > 0:
                pop_bonus = math.log10(population) - 3
                score += max(0, pop_bonus) * 3

            if orig.lower() in ("киев", "kyiv", "москва", "moscow"):
                if event_hits == 0 and not has_direct_verb_before(text, phrase):
                    score -= 10

            score -= pos_in_text * 0.05

            candidates.append((score, orig, lat, lng, population))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: -x[0])
    best_score, best_name, best_lat, best_lng, pop = candidates[0]
    if best_score < 5:
        return None, None
    return (best_lat, best_lng), best_name


def is_cancellation(text):
    tl = text.lower()
    has_cancel = any(c in tl for c in CANCEL_WORDS)
    if not has_cancel:
        return False
    has_alert = any(a in tl for a in ALERT_WORDS)
    return has_alert


def classify_event(text):
    tl = text.lower()
    if is_cancellation(text):
        return None
    if any(w in tl for w in ["тревога", "alert", "сирена", "тривога", "воздушная", "повітряна", "опасность", "угроза", "бпла"]):
        return "Air Raid Alert"
    if any(w in tl for w in ["удар", "strike", "взрыв", "explosion", "прилёт", "приліт", "обстр", "дрон", "ракет", "пво", "уразили", "уражено"]):
        return "Military Strike"
    if any(w in tl for w in ["наступление", "offensive", "атака", "attack", "наступ", "прорыв", "штурм"]):
        return "Military Offensive"
    if any(w in tl for w in ["бои", "battle", "fight", "бой", "бій", "боях", "позиции"]):
        return "Military Operation"
    return None


def make_dedup_key(ev):
    if ev.get("url"):
        return ev["url"]
    return ev["channel"] + "|" + ev.get("description", "")[:80]


def jitter_coords(lat, lng, radius_km):
    deg_lat_per_km = 1.0 / 111.0
    deg_lng_per_km = 1.0 / (111.0 * math.cos(math.radians(lat)) + 0.0001)
    dlat = random.uniform(-radius_km, radius_km) * deg_lat_per_km
    dlng = random.uniform(-radius_km, radius_km) * deg_lng_per_km
    return lat + dlat, lng + dlng


def radius_for_count(count):
    if count <= 3:
        return 1.5
    elif count <= 10:
        return 3.0
    elif count <= 20:
        return 5.0
    else:
        return 8.0


def apply_cancellations(raw_events, cancellations):
    if not cancellations:
        return raw_events
    cancels_by_city = {}
    for c in cancellations:
        cancels_by_city.setdefault(c['city'].lower(), []).append(c['date'])

    filtered = []
    removed = 0
    for ev in raw_events:
        if ev['event_type'] == 'Air Raid Alert':
            city_low = ev['location'].lower()
            ev_date = ev.get('date') or ''
            if city_low in cancels_by_city:
                cancelled = False
                for cancel_date in cancels_by_city[city_low]:
                    if cancel_date and ev_date and cancel_date > ev_date:
                        cancelled = True
                        break
                if cancelled:
                    removed += 1
                    continue
        filtered.append(ev)

    print(f"   Убрано устаревших тревог (отбой): {removed}")
    return filtered


def main():
    load_settlements()

    raw_events = []
    cancellations = []
    seen_texts = set()
    seen_dedup = set()
    duplicates = 0
    stats = {}
    no_match = 0

    for channel in CHANNELS:
        print(f"Парсим @{channel}...")
        html = fetch_channel(channel)
        if not html:
            stats[channel] = 0
            continue
        posts = extract_posts(html)
        print(f"  Найдено постов: {len(posts)}")
        matched = 0

        channel_country = CHANNEL_COUNTRY.get(channel, "OSINT")

        for post in posts:
            text = post["text"]
            key = text[:80]
            if key in seen_texts:
                continue
            seen_texts.add(key)

            event_type = classify_event(text)
            if not event_type:
                continue

            # 1. Сначала ищем алиасы транслитерации (Ульяновськ, Курськ и т.д.)
            coords, city, country = find_alias(text)

            # 2. Если алиас не найден — ищем обычный город
            if not coords:
                coords, city = find_best_city(text, channel_country)
                country = channel_country if channel_country in ("UA", "RU") else "OSINT"

            if not coords:
                no_match += 1
                continue

            if is_cancellation(text):
                cancellations.append({
                    'city': city,
                    'date': post['date'],
                    'lat': coords[0],
                    'lng': coords[1],
                })
                continue

            matched += 1

            ev = {
                "id": len(raw_events) + 1,
                "url": post["url"] or f"https://t.me/s/{channel}",
                "date": post["date"],
                "event_type": event_type,
                "location": city,
                "country": country,
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

            raw_events.append(ev)

        stats[channel] = matched
        print(f"  Совпало: {matched}")
        time.sleep(1)

    print(f"\n🚫 Отмен тревог найдено: {len(cancellations)}")
    print("🧹 Убираю устаревшие тревоги...")
    raw_events = apply_cancellations(raw_events, cancellations)

    coord_counter = Counter()
    for ev in raw_events:
        coord_key = (round(ev["lat"], 3), round(ev["lng"], 3))
        coord_counter[coord_key] += 1

    print(f"\n🔀 Применяю jitter к {len(raw_events)} событиям...")
    for ev in raw_events:
        coord_key = (round(ev["lat"], 3), round(ev["lng"], 3))
        count = coord_counter[coord_key]
        radius = radius_for_count(count)
        ev["lat"], ev["lng"] = jitter_coords(ev["lat"], ev["lng"], radius)

    output = "window.TG_DATA = " + json.dumps({"events": raw_events}, ensure_ascii=False) + ";"
    with open("data/telegram-events.js", "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✅ Итого: {len(raw_events)} событий")
    print(f"   Отброшено дубликатов: {duplicates}")
    print(f"   Постов без совпадений по н.п.: {no_match}")

    print("\n📊 Статистика по каналам:")
    for ch, count in sorted(stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  @{ch}: {count}")

    print("\n📍 Топ-15 населённых пунктов:")
    city_counter = Counter(ev["location"] for ev in raw_events)
    for city, count in city_counter.most_common(15):
        print(f"  {city}: {count}")


if __name__ == "__main__":
    main()
