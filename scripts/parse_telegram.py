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
    "ruporruss", "grohot_pgr", "russiamonitoring_radar_bpla",
]

CHANNEL_COUNTRY = {
    "kpszsu": "UA", "GeneralStaffZSU": "UA", "operativnoZSU": "UA",
    "ukrpravda_news": "UA", "uniannet": "UA", "DeepStateUA": "UA",
    "amk_mapping": "UA", "OsintFlow": "UA", "ukraine_observer": "UA",
    "rybar": "RU", "voenkorKotenok": "RU", "wargonzo": "RU",
    "dva_majors": "RU", "readovkanews": "RU", "tass_agency": "RU",
    "militarysummary": "RU", "lost_armour": "RU",
    "UAWeapons": "OSINT", "Osinttechnical": "OSINT", "informnapalm": "OSINT",
    "AerisRimor": "UA", "monitoringwar": "UA",
    "sputnikrussia_radar": "RU", "radar_rf": "RU", "locatorru": "RU",
    "ruporruss": "RU", "grohot_pgr": "RU", "russiamonitoring_radar_bpla": "RU",
}

EVENT_CONTEXT = ["удар", "обстр", "тревог", "взрыв", "прилёт", "приліт", "атак",
                 "бой", "наступлен", "наступ", "штурм", "бпла", "дрон", "ракет",
                 "пво", "по ", "в ", "на ", "оборон"]

NOISE_CONTEXT = ["заяв", "сообщ", "минобороны",
                 "по данным", "по словам", "отметил", "подчеркн",
                 "написал", "передаёт", "передает", "цитирует",
                 "комментар", "пресс-служб"]

SETTLEMENTS_BY_NAME = {}


def load_settlements():
    global SETTLEMENTS_BY_NAME
    path = 'data/settlements.js'
    if not os.path.exists(path):
        print("  ⚠️ data/settlements.js не найден — работаю только по крупным городам", file=sys.stderr)
        return
    print("Загружаю базу населённых пунктов...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('window.SETTLEMENTS = ', '').rstrip(';').rstrip()
    data = json.loads(json_str)
    for s in data:
        name_low = s['name'].lower()
        SETTLEMENTS_BY_NAME.setdefault(name_low, []).append(
            (s['lat'], s['lng'], s['country'], s['name'], s.get('population', 0))
        )
    print(f"  Загружено {len(data)} записей")


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


def find_best_city(text):
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
            coords_list = SETTLEMENTS_BY_NAME[phrase]
            best = max(coords_list, key=lambda x: x[4])
            lat, lng, country, orig, population = best

            pos_in_text = tl.find(phrase)
            if pos_in_text < 0:
                pos_in_text = 0
            before = tl[max(0, pos_in_text-60):pos_in_text]
            after = tl[pos_in_text+len(phrase):pos_in_text+len(phrase)+60]

            score = 0
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
                if event_hits == 0:
                    score -= 5

            score -= pos_in_text * 0.05

            candidates.append((score, orig, lat, lng, population))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: -x[0])
    best_score, best_name, best_lat, best_lng, pop = candidates[0]
    return (best_lat, best_lng), best_name


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


def country_by_coords_or_context(lat, lng, channel):
    if 44 <= lat <= 53 and 22 <= lng <= 41:
        return "UA"
    if 41 <= lat <= 82 and 19 <= lng <= 180:
        return "RU"
    return CHANNEL_COUNTRY.get(channel, "OSINT")


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


def main():
    load_settlements()

    raw_events = []
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

        for post in posts:
            text = post["text"]
            key = text[:80]
            if key in seen_texts:
                continue
            seen_texts.add(key)

            coords, city = find_best_city(text)
            if not coords:
                no_match += 1
                continue
            matched += 1

            ev = {
                "id": len(raw_events) + 1,
                "url": post["url"] or f"https://t.me/s/{channel}",
                "date": post["date"],
                "event_type": classify_event(text),
                "location": city,
                "country": country_by_coords_or_context(coords[0], coords[1], channel),
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
        print(f"  Совпало с населёнными пунктами: {matched}")
        time.sleep(1)

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
    print(f"   Постов без совпадений: {no_match}")

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
