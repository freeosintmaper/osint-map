import urllib.request
import zipfile
import io
import json
import os

URLS = {
    'RU': 'https://download.geonames.org/export/dump/RU.zip',
    'UA': 'https://download.geonames.org/export/dump/UA.zip',
}

MIN_POPULATION = 5000

EXCLUDE_NAMES = {
    'иран', 'ирак', 'китай', 'турция', 'польша', 'германия', 'франция',
    'беларусь', 'белоруссия', 'молдова', 'румыния', 'словакия', 'венгрия',
    'сша', 'канада', 'британия', 'англия', 'япония', 'корея', 'израиль',
    'палестина', 'сирия', 'ливан', 'египет', 'ливия', 'судан', 'афганистан',
    'пакистан', 'индия', 'монголия', 'грузия', 'армения', 'азербайджан',
    'казахстан', 'узбекистан', 'киргизия', 'таджикистан', 'туркменистан',
    'краснодарский', 'ставропольский', 'ростовская', 'белгородская',
    'брянская', 'курская', 'воронежская', 'орловская', 'тульская',
    'московская', 'ленинградская', 'новосибирская', 'оренбургская',
    'саратовская', 'волгоградская', 'астраханская', 'самарская',
    'тверская', 'псковская', 'смоленская', 'калужская', 'рязанская',
    'тамбовская', 'липецкая', 'пензенская', 'ульяновская',
    'полтавская', 'харьковская', 'киевская', 'львовская', 'одесская',
}


def process_country(code, zip_bytes):
    settlements = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        txt_name = f"{code}.txt"
        if txt_name not in z.namelist():
            print(f"  {txt_name} не найден в архиве")
            return settlements
        with z.open(txt_name) as f:
            for line in f:
                parts = line.decode('utf-8').split('\t')
                if len(parts) < 19:
                    continue
                if parts[6] != 'P':
                    continue
                try:
                    population = int(parts[14]) if parts[14] else 0
                except ValueError:
                    population = 0
                if population < MIN_POPULATION:
                    continue

                name = parts[1]
                alt_names = parts[3].split(',') if parts[3] else []
                lat = float(parts[4])
                lng = float(parts[5])

                all_names = set()
                if name:
                    all_names.add(name)
                for alt in alt_names:
                    alt = alt.strip()
                    if alt and 3 <= len(alt) <= 40 and any('а' <= c.lower() <= 'я' for c in alt):
                        all_names.add(alt)

                all_names = {n for n in all_names if n.lower() not in EXCLUDE_NAMES}
                if not all_names:
                    continue

                for n in all_names:
                    settlements.append({
                        'name': n,
                        'lat': lat,
                        'lng': lng,
                        'country': code,
                        'population': population,
                    })
    return settlements


def main():
    all_settlements = []
    for code, url in URLS.items():
        print(f"Скачиваю {code}...")
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                zip_bytes = r.read()
            print(f"  Размер: {len(zip_bytes) / 1024 / 1024:.1f} MB")
            settlements = process_country(code, zip_bytes)
            print(f"  Крупных населённых пунктов: {len(settlements)}")
            all_settlements.extend(settlements)
        except Exception as e:
            print(f"  Ошибка: {e}")

    best_by_name = {}
    for s in all_settlements:
        key = s['name'].lower()
        existing = best_by_name.get(key)
        if not existing or s['population'] > existing['population']:
            best_by_name[key] = s

    unique = list(best_by_name.values())
    print(f"\nВсего уникальных названий: {len(unique)}")

    os.makedirs('data', exist_ok=True)
    output = "window.SETTLEMENTS = " + json.dumps(unique, ensure_ascii=False) + ";"
    with open('data/settlements.js', 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"Сохранено в data/settlements.js ({len(output) / 1024:.1f} KB)")


if __name__ == '__main__':
    main()
