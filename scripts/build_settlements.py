"""
Скачивает GeoNames (RU + UA), конвертирует в data/settlements.js.
Берёт кириллические и латинские альтернативные названия.
Запускается автоматически в GitHub Actions перед парсингом.
"""

import urllib.request
import zipfile
import io
import json
import os
import re
import sys

GEONAMES_URL = 'https://download.geonames.org/export/dump/{cc}.zip'
COUNTRIES = ['RU', 'UA']
OUTPUT = 'data/settlements.js'

# Лимиты на количество альтернатив (чтобы файл не раздулся)
MAX_CYR_ALTS = 8
MAX_LAT_ALTS = 3
MAX_NAME_LEN = 50
MIN_NAME_LEN = 2


def fetch_zip(url, target_file):
    print(f"⬇️  {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    print(f"   {len(data) / 1024 / 1024:.1f} МБ скачано")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        with z.open(target_file) as f:
            return f.read().decode('utf-8')


def is_cyrillic(s):
    return bool(re.search(r'[а-яёА-ЯЁіїєґІЇЄҐ]', s))


def is_latin(s):
    # Только латиница (без кириллицы)
    if re.search(r'[а-яёА-ЯЁіїєґІЇЄҐ]', s):
        return False
    return bool(re.search(r'[a-zA-Z]', s))


def parse_geonames(text, country_code):
    rows = []
    for line in text.split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 19:
            continue
        try:
            feature_class = parts[6]
            feature_code = parts[7]
            if feature_class != 'P':
                continue
            if not feature_code.startswith('PPL'):
                continue

            name = parts[1].strip()
            asciiname = parts[2].strip()
            alternatenames = parts[3].strip()
            lat = float(parts[4])
            lng = float(parts[5])
            population = int(parts[14]) if parts[14].isdigit() else 0

            rows.append({
                'name': name,
                'asciiname': asciiname,
                'alternates': [a.strip() for a in alternatenames.split(',') if a.strip()],
                'lat': lat,
                'lng': lng,
                'country': country_code,
                'population': population,
            })
        except Exception:
            continue
    return rows


def build():
    all_rows = []
    for cc in COUNTRIES:
        text = fetch_zip(GEONAMES_URL.format(cc=cc), f'{cc}.txt')
        rows = parse_geonames(text, cc)
        print(f"📦 {cc}: {len(rows)} населённых пунктов")
        all_rows.extend(rows)

    settlements = []
    seen = set()

    for row in all_rows:
        names = set()

        # Основное название
        if row['name']:
            names.add(row['name'])

        # ASCII-название (обычно латиница)
        if row['asciiname'] and row['asciiname'] != row['name']:
            names.add(row['asciiname'])

        # Кириллические альтернативы (русский, украинский)
        cyr_alts = [
            a for a in row['alternates']
            if is_cyrillic(a) and MIN_NAME_LEN <= len(a) <= MAX_NAME_LEN
        ]
        for a in cyr_alts[:MAX_CYR_ALTS]:
            names.add(a)

        # Латиница (английский, транслит)
        lat_alts = [
            a for a in row['alternates']
            if is_latin(a) and 4 <= len(a) <= 40
        ]
        for a in lat_alts[:MAX_LAT_ALTS]:
            names.add(a)

        # Сохраняем все варианты как отдельные записи
        for n in names:
            n = n.strip()
            if len(n) < MIN_NAME_LEN or len(n) > MAX_NAME_LEN:
                continue
            key = (n.lower(), row['country'])
            if key in seen:
                continue
            seen.add(key)
            settlements.append({
                'name': n,
                'lat': row['lat'],
                'lng': row['lng'],
                'country': row['country'],
                'population': row['population'],
            })

    print(f"✅ Итого записей (с алиасами): {len(settlements)}")

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write('window.SETTLEMENTS = ')
        json.dump(settlements, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';')

    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"💾 {OUTPUT}: {size:.1f} МБ")


if __name__ == '__main__':
    try:
        build()
    except Exception as e:
        print(f"❌ Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
