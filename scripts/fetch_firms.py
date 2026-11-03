"""Загрузка тепловых аномалий NASA FIRMS для территории Украины и России.
Требуется FIRMS_MAP_KEY из GitHub Secrets.

При сетевой ошибке, неожиданном формате ответа или подозрительно пустом ответе
существующий набор данных не перезаписывается.
"""

import csv
import io
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

BBOX = "22,44,180,82"
DAYS = 1
SOURCES = ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT")
MAX_RECORDS = 3000
OUTPUT_PATH = "data/firms-fires.json"

MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "").strip()

if not MAP_KEY:
    print("❌ FIRMS_MAP_KEY не задан в GitHub Secrets", file=sys.stderr)
    sys.exit(1)


def fetch_firms(source):
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{source}/{BBOX}/{DAYS}"
    )
    print(f"Загружаю NASA FIRMS: {source}")
    req = urllib.request.Request(url, headers={"User-Agent": "OSINT-map/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"{source}: NASA FIRMS вернул HTTP {response.status}")
        data = response.read().decode("utf-8-sig", errors="strict")
    if not data.strip():
        raise ValueError(f"{source}: NASA FIRMS вернул пустой ответ")
    return data


def parse_firms_csv(data):
    if not isinstance(data, str) or not data.strip():
        raise ValueError("CSV NASA FIRMS пуст")

    reader = csv.DictReader(io.StringIO(data.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("В ответе NASA FIRMS отсутствует CSV-заголовок")

    reader.fieldnames = [
        name.strip().lstrip("\ufeff").lower() if name else ""
        for name in reader.fieldnames
    ]
    required = {"latitude", "longitude"}
    if not required.issubset(set(reader.fieldnames)):
        raise ValueError(
            "Неожиданный CSV-формат NASA FIRMS: отсутствуют latitude/longitude"
        )

    features = []
    for row in reader:
        try:
            lat_raw = row.get("latitude")
            lng_raw = row.get("longitude")
            if not lat_raw or not lng_raw:
                continue

            lat = float(lat_raw)
            lng = float(lng_raw)
            if not (math.isfinite(lat) and math.isfinite(lng)):
                continue
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue

            brightness_raw = row.get("bright_ti4") or row.get("brightness") or "300"
            brightness = float(brightness_raw)
            frp = float(row.get("frp") or 0)
            if not (math.isfinite(brightness) and math.isfinite(frp)):
                continue

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {
                    "brightness": brightness,
                    "satellite": row.get("satellite", ""),
                    "acq_date": row.get("acq_date", ""),
                    "acq_time": row.get("acq_time", ""),
                    "confidence": row.get("confidence", ""),
                    "frp": frp,
                },
            })
        except (TypeError, ValueError):
            continue

    features.sort(key=lambda feature: -feature["properties"]["brightness"])
    return features[:MAX_RECORDS]


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json_atomically(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, separators=(",", ":"))
        output_file.write("\n")
    os.replace(temp_path, path)


def main():
    try:
        features = []
        successful_sources = []
        errors = []
        for source in SOURCES:
            try:
                source_features = parse_firms_csv(fetch_firms(source))
                features.extend(source_features)
                successful_sources.append(source)
                print(f"{source}: {len(source_features)} точек")
            except Exception as source_error:
                errors.append(f"{source}: {source_error}")
                print(f"⚠️ Источник недоступен: {source_error}", file=sys.stderr)

        if not successful_sources:
            raise RuntimeError("Не удалось получить данные ни с одного спутника. " + " | ".join(errors))

        # Дедупликация по спутнику, координатам и времени наблюдения.
        unique = {}
        for feature in features:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            key = (
                props.get("satellite"), props.get("acq_date"), props.get("acq_time"),
                round(coords[0], 5), round(coords[1], 5)
            )
            unique[key] = feature
        features = sorted(
            unique.values(),
            key=lambda feature: -feature["properties"]["brightness"]
        )[:MAX_RECORDS]
        print(f"Итого уникальных точек: {len(features)}; источники: {', '.join(successful_sources)}")

        if not features and os.path.exists(OUTPUT_PATH):
            with open(OUTPUT_PATH, "r", encoding="utf-8") as existing_file:
                previous = json.load(existing_file)
            if previous.get("features"):
                raise RuntimeError(
                    "NASA FIRMS вернул 0 валидных точек; существующие данные сохранены."
                )

        output = {
            "type": "FeatureCollection",
            "generated": utc_timestamp(),
            "sources": successful_sources,
            "source_errors": errors,
            "features": features,
        }
        write_json_atomically(OUTPUT_PATH, output)
        print(f"✅ Сохранено в {OUTPUT_PATH}")
    except Exception as error:
        print(f"❌ Ошибка FIRMS: {error}. Существующий файл не перезаписан.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
