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

ABBREVIATIONS = {
    "мена", "mena", "сша", "оон", "нато", "ес", "eu", "вс", "пво", "рлс", "зрк",
    "бпла", "бпа", "ттх", "орб", "орг", "мто", "асу", "гпс", "гпр", "су", "мк",
    "пи", "пр", "рсзо", "опк", "кндр", "кнр", "рф", "уа", "usa", "nato", "un",
    "азия", "африка", "европа",
}

# КОРОТКИЕ КОРНИ — совпадают в любом падеже
# Формат: корень → [lat, lng, отображаемое имя, страна]
TRANSLIT_ALIASES = {
    # Украинские названия российских городов и областей
    "ульяновськ": [54.3142, 48.4031, "Ульяновск", "RU"],
    "воронезьк": [51.6720, 39.1843, "Воронеж", "RU"],
    "воронез": [51.6720, 39.1843, "Воронеж", "RU"],
    "курськ": [51.7304, 36.1926, "Курск", "RU"],
    "бєлгород": [50.5952, 36.5873, "Белгород", "RU"],
    "брянськ": [53.2435, 34.3639, "Брянск", "RU"],
    "орловськ": [52.9651, 36.0785, "Орел", "RU"],
    "орловсь": [52.9651, 36.0785, "Орел", "RU"],
    "липецьк": [52.6031, 39.5708, "Липецк", "RU"],
    "тамбовськ": [52.7212, 41.4523, "Тамбов", "RU"],
    "смоленськ": [54.7826, 32.0453, "Смоленск", "RU"],
    "тверськ": [56.8587, 35.9176, "Тверь", "RU"],
    "псковськ": [57.8194, 28.3318, "Псков", "RU"],
    "новгородськ": [58.5215, 31.2755, "Новгород", "RU"],
    "мурманськ": [68.9585, 33.0827, "Мурманск", "RU"],
    "архангельськ": [64.5393, 40.5182, "Архангельск", "RU"],
    "астраханськ": [46.3497, 48.0408, "Астрахань", "RU"],
    "челябінськ": [55.1644, 61.4368, "Челябинск", "RU"],
    "єкатеринбурз": [56.8389, 60.6057, "Екатеринбург", "RU"],
    "омськ": [54.9885, 73.3242, "Омск", "RU"],
    "новосибірськ": [55.0084, 82.9357, "Новосибирск", "RU"],
    "іркутськ": [52.2871, 104.3051, "Иркутск", "RU"],
    "хабаровськ": [48.4827, 135.0838, "Хабаровск", "RU"],
    "волгоградськ": [48.7080, 44.5133, "Волгоград", "RU"],
    "саратовськ": [51.5336, 46.0343, "Саратов", "RU"],
    "самарськ": [53.1959, 50.1061, "Самара", "RU"],
    "казанськ": [55.8304, 49.0661, "Казань", "RU"],
    "нижньогородськ": [56.3269, 44.0059, "Нижний Новгород", "RU"],
    "тульськ": [54.1961, 37.6182, "Тула", "RU"],
    "калузьк": [54.5138, 36.2612, "Калуга", "RU"],
    "рязанськ": [54.6269, 39.6916, "Рязань", "RU"],
    "пензенськ": [53.2007, 45.0046, "Пенза", "RU"],
    "оренбурзьк": [51.7727, 55.0988, "Оренбург", "RU"],
    "тюменськ": [57.1522, 65.5272, "Тюмень", "RU"],
    "кемеровськ": [55.3547, 86.0873, "Кемерово", "RU"],
    "ростовськ": [47.2225, 39.7188, "Ростов", "RU"],
    "краснодарськ": [45.0355, 38.9753, "Краснодар", "RU"],
    "ставропольськ": [45.0428, 41.9734, "Ставрополь", "RU"],
    "приморськ": [43.1155, 131.8855, "Владивосток", "RU"],

    # Российские названия украинских городов и областей
    "київськ": [50.4501, 30.5234, "Киев", "UA"],
    "киевск": [50.4501, 30.5234, "Киев", "UA"],
    "львівськ": [49.8397, 24.0297, "Львов", "UA"],
    "львовск": [49.8397, 24.0297, "Львов", "UA"],
    "одеськ": [46.4775, 30.7326, "Одесса", "UA"],
    "одесск": [46.4775, 30.7326, "Одесса", "UA"],
    "харківськ": [49.9935, 36.2304, "Харьков", "UA"],
    "харьковск": [49.9935, 36.2304, "Харьков", "UA"],
    "донецьк": [48.0159, 37.8029, "Донецк", "UA"],
    "луганськ": [48.5740, 39.3078, "Луганск", "UA"],
    "запорізьк": [47.8388, 35.1396, "Запорожье", "UA"],
    "запорожск": [47.8388, 35.1396, "Запорожье", "UA"],
    "херсонськ": [46.6354, 32.6169, "Херсон", "UA"],
    "миколаївськ": [46.9750, 31.9946, "Николаев", "UA"],
    "николаевск": [46.9750, 31.9946, "Николаев", "UA"],
    "дніпропетровськ": [48.4647, 35.0462, "Днепр", "UA"],
    "полтавськ": [49.5883, 34.5514, "Полтава", "UA"],
    "сумськ": [50.9077, 34.7981, "Сумы", "UA"],
    "чернігівськ": [51.4982, 31.2893, "Чернигов", "UA"],
    "житомирськ": [50.2547, 28.6587, "Житомир", "UA"],
    "вінницьк": [49.2331, 28.4682, "Винница", "UA"],
    "кіровоградськ": [48.5079, 32.2623, "Кропивницкий", "UA"],
    "черкаськ": [49.4444, 32.0598, "Черкассы", "UA"],
    "рівненськ": [50.6199, 26.2516, "Ровно", "UA"],
    "волинськ": [50.7472, 25.3254, "Луцк", "UA"],
    "тернопільськ": [49.5535, 25.5948, "Тернополь", "UA"],
    "хмельницьк": [49.4229, 26.9871, "Хмельницкий", "UA"],
    "франківськ": [48.9226, 24.7111, "Ивано-Франковск", "UA"],
    "закарпатськ": [48.6208, 22.2879, "Ужгород", "UA"],
    "чернівецьк": [48.2917, 25.9354, "Черновцы", "UA"],
}

# ОБЯЗАТЕЛЬНЫЕ паттерны: событие, только если рядом с городом есть ТАКОЕ
EVENT_PATTERNS = [
    # Удар по X / X под ударом / удар в X
    r'удар\w*\s+(?:по|на|в)\s+',
    r'ударил\w*\s+(?:по|на|в)\s+',
    r'ударили\s+по\s+',
    r'під\s+ударом',
    r'под\s+ударом',
    r'под\s+атакой',
    r'під\s+атакою',
    r'подверг\w*\s+атаке',
    r'зазнав\w*\s+удар',
    # Обстрел X / обстреляли X
    r'обстрел\w*\s+',
    r'обстріл\w*\s+',
    r'обстрелял\w*\s+',
    r'обстрілял\w*\s+',
    # Взрыв в X / прилёт в X
    r'взрыв\w*\s+(?:в|на|по)\s+',
    r'вибух\w*\s+(?:у|в|на)\s+',
    r'прилёт\w*\s+(?:в|по|на)\s+',
    r'приліт\w*\s+(?:в|у|по|на)\s+',
    # Атака на X / атаковали X
    r'атак\w*\s+(?:на|в|по)\s+',
    r'атакувал\w*\s+',
    r'атакуют\s+',
    # Тревога в X
    r'тревог\w*\s+(?:в|на)\s+',
    r'тривог\w*\s+(?:у|в|на)\s+',
    r'опасность\s+(?:в|на)\s+',
    r'небезпек\w*\s+(?:у|в|на)\s+',
    # Уражено / поражено в X
    r'уражено\s+(?:в|у|на)\s+',
    r'поражено\s+(?:в|на)\s+',
    r'уразили\s+',
    r'поразили\s+',
    # БПЛА над X / курс на X
    r'бпла\s+(?:над|на|в|курс)',
    r'дрон\w*\s+(?:над|на|в|курс)',
    r'курс\w*\s+(?:на|в)\s+',
]

# ГЛАГОЛЫ-ИСТОЧНИКИ: если рядом — это не цель, а источник
SOURCE_VERBS = [
    r'атаковали\s+с', r'атакуют\s+с', r'атакували\s+з',
    r'запустили\s+с', r'запускают\s+с', r'запустили\s+з',
    r'вылетели\s+с', r'вылетают\s+с', r'вилетіли\s+з',
    r'прилетели\s+с', r'курс\s+с', r'курсом\s+с',
    r'с\s+территории', r'з\s+території',
    r'с\s+направления', r'з\s+напрямку',
]

CANCEL_WORDS = ["отбой", "отменена", "отменён", "отменен",
                "завершена", "завершён", "завершен",
                "прекращена", "прекращён", "прекращен",
                "окончена", "угроза миновала", "опасность миновала",
                "відбій", "скасована", "завершено"]

ALERT_WORDS = ["тревог", "опасност", "угроз", "alert", "бпла", "ракет",
               "тривог", "небезпек", "загроз"]

MILITARY_TERMS = ["рлс", "зрк", "с-300", "с-400", "с-500", "бук ", "панцирь",
                  "тор ", "тюльпан", "град ", "ураган", "смерч",
                  "искандер", "кинжал", "калибр", "шахед", "герань",
                  "ланцет", "точка-у", "тос-", "оса ", "стрела",
                  "шилка", "тунгуска", "радиолокацион", "комплекс",
                  "установк", "нпз", "завод", "підприємств"]

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
    "точка", "печора", "акация", "гиацинт", "пион", "мена",
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
        if name_low in STOP_SETTLEMENTS or name_low in ABBREVIATIONS:
            skipped += 1
            continue
        SETTLEMENTS_BY_NAME.setdefault(name_low, []).append(
            (s['lat'], s['lng'], s['country'], s['name'], s.get('population', 0))
        )
    print(f"  Загружено {len(data)} записей, пропущено: {skipped}")


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


def has_event_pattern_near(text, phrase, window=80):
    """КЛЮЧЕВАЯ ФУНКЦИЯ: рядом с городом ДОЛЖЕН быть EVENT_PATTERN."""
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    # Смотрим окно вокруг города
    before = tl[max(0, idx-window):idx]
    after = tl[idx+len(phrase):idx+len(phrase)+window]
    full = before + " " + after
    for pat in EVENT_PATTERNS:
        if re.search(pat, full):
            return True
    return False


def has_source_verb_near(text, phrase, window=60):
    """Если рядом SOURCE_VERB — это не цель события."""
    tl = text.lower()
    idx = tl.find(phrase.lower())
    if idx < 0:
        return False
    full = tl[max(0, idx-window):idx+len(phrase)+window]
    for pat in SOURCE_VERBS:
        if re.search(pat, full):
            return True
    return False


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


def find_alias(text, channel_country):
    """Ищет алиасы-корни. Возвращает координаты, имя, страну."""
    tl = text.lower()
    # Сортируем по длине — длинные корни первыми
    for key in sorted(TRANSLIT_ALIASES.keys(), key=lambda k: -len(k)):
        if key not in tl:
            continue
        coords = TRANSLIT_ALIASES[key]
        alias_country = coords[3]

        # Проверяем, есть ли рядом EVENT_PATTERN
        if not has_event_pattern_near(text, key, window=80):
            continue
        # Проверяем, нет ли рядом глагола-источника
        if has_source_verb_near(text, key, window=60):
            continue
        # Проверяем, не милитарный термин
        if is_military_term_context(text, key):
            continue

        return (coords[0], coords[1]), coords[2], coords[3]
    return None, None, None


def find_best_city(text, channel_country):
    """Радикальный поиск: только если рядом EVENT_PATTERN и нет SOURCE_VERB."""
    if not SETTLEMENTS_BY_NAME:
        return None, None, None

    tl = text.lower()
    words = re.findall(r'[а-яёa-zа-їієґ0-9\-]+', tl)
    if not words:
        return None, None, None

    candidates = []
    N = len(words)

    for size in (3, 2, 1):
        for i in range(N - size + 1):
            phrase = ' '.join(words[i:i+size])
            if phrase not in SETTLEMENTS_BY_NAME:
                continue
            if phrase in ABBREVIATIONS:
                continue
            if is_military_term_context(text, phrase):
                continue

            # ЖЁСТКОЕ ТРЕБОВАНИЕ: рядом есть EVENT_PATTERN
            if not has_event_pattern_near(text, phrase, window=80):
                continue
            # ЖЁСТКОЕ ТРЕБОВАНИЕ: нет SOURCE_VERB рядом
            if has_source_verb_near(text, phrase, window=60):
                continue

            coords_list = SETTLEMENTS_BY_NAME[phrase]

            # Фильтр по стране канала
            if channel_country in ("UA", "RU"):
                filtered = [c for c in coords_list if c[2] == channel_country]
                if not filtered:
                    continue
                best = max(filtered, key=lambda x: x[4])
            else:
                best = max(coords_list, key=lambda x: x[4])

            lat, lng, country, orig, population = best

            pos_in_text = tl.find(phrase)
            if pos_in_text < 0:
                pos_in_text = 0

            # Score только для ранжирования между валидными кандидатами
            score = 0
            # Город ближе к началу — приоритет
            if pos_in_text < 150:
                score += 20
            # Крупнее население — приоритет
            if population > 0:
                pop_bonus = math.log10(population) - 3
                score += max(0, pop_bonus) * 3
            # Позиция — чем раньше, тем лучше
            score -= pos_in_text * 0.05

            candidates.append((score, orig, lat, lng, country))

    if not candidates:
        return None, None, None

    candidates.sort(key=lambda x: -x[0])
    best_score, best_name, best_lat, best_lng, best_country = candidates[0]
    return (best_lat, best_lng), best_name, best_country


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
    if any(w in tl for w in ["тревога", "тривога", "alert", "сирена",
                             "воздушная тревога", "повітряна тривога",
                             "опасность", "небезпека", "угроза", "загроза"]):
        return "Air Raid Alert"
    if any(w in tl for w in ["удар", "обстр", "взрыв", "вибух", "прилёт", "приліт",
                             "ракет", "пво", "уразили", "уражено", "поразили",
                             "поражено", "бпла", "дрон", "шахед"]):
        return "Military Strike"
    if any(w in tl for w in ["наступление", "наступ", "атака", "attack", "прорыв", "штурм"]):
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

            # 1. Сначала ищем алиасы-корни
            coords, city, country = find_alias(text, channel_country)

            # 2. Потом обычный поиск с жёстким фильтром
            if not coords:
                coords, city, country = find_best_city(text, channel_country)

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
