import urllib.request
import zipfile
import io
import json
import os

# GeoNames: скачиваем все населённые пункты РФ и Украины
# Формат: geonameid, name, asciiname, alternatenames, lat, lng, ...
# feature class 'P' = populated places

URLS = {
    'RU': 'https://download.geonames.org/export/dump/RU.zip',
    'UA': 'https://download.geonames.org/export/dump/UA.zip',
}

def process_country(code, zip_bytes):
    settlements = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        # Ищем файл с кодом страны
        txt_name = f"{code}.txt"
        if txt_name not in z.namelist():
            print(f"  {txt_name} не найден в архиве")
            return settlements
        with z.open(txt_name) as f:
            for line in f:
                parts = line.decode('utf-8').split('\t')
                if len(parts) < 19:
                    continue
                # feature_class = 'P' (populated place)
                if parts[6] != 'P':
                    continue
                name = parts[1]  # основное название
                # alternatenames — через запятую, могут содержать русские варианты
                alt_names = parts[3].split(',') if parts[3] else []
                lat = float(parts[4])
                lng = float(parts[5])

                # Собираем все варианты названий
                all_names = set()
                if name:
                    all_names.add(name)
                for alt in alt_names:
                    alt = alt.strip()
                    # Фильтруем: только кириллица, длина 3-40
                    if alt and 3 <= len(alt) <= 40 and any('а' <= c.lower() <= 'я' for c in alt):
                        all_names.add(alt)

                for n in all_names:
                    settlements.append({
                        'name': n,
                        'lat': lat,
                        'lng': lng,
                        'country': code
                    })
    return settlements

def main():
    all_settlements = []
    for code, url in URLS.items():
        print(f"Скачиваю {code}...")
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                zip_bytes = r.read()
            print(f"  Размер: {len(zip_bytes) / 1024 / 1024:.1f} MB")
            settlements = process_country(code, zip_bytes)
            print(f"  Населённых пунктов: {len(settlements)}")
            all_settlements.extend(settlements)
        except Exception as e:
            print(f"  Ошибка: {e}")

    # Дедупликация по (name, lat, lng)
    seen = set()
    unique = []
    for s in all_settlements:
        key = (s['name'].lower(), round(s['lat'], 3), round(s['lng'], 3))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    print(f"\nВсего уникальных записей: {len(unique)}")

    # Сохраняем как JS-файл, чтобы карта и парсер могли читать
    os.makedirs('data', exist_ok=True)
    output = "window.SETTLEMENTS = " + json.dumps(unique, ensure_ascii=False) + ";"
    with open('data/settlements.js', 'w', encoding='utf-8') as f:
        f.write(output)
    print("Сохранено в data/settlements.js")

if __name__ == '__main__':
    main()
