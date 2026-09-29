"""
Загрузка тепловых аномалий NASA FIRMS для территории Украины и России.
Требуется MAP_KEY из GitHub Secrets (FIRMS_MAP_KEY).
"""

import urllib.request
import csv
import json
import io
import sys
import os
from datetime import datetime

BBOX = "22,44,180,82"
DAYS = 1
SOURCE = "VIIRS_SNPP_NRT"
MAX_RECORDS = 3000

MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "").strip()

if not MAP_KEY:
    print("❌ FIRMS_MAP_KEY не задан в GitHub Secrets", file=sys.stderr)
    sys.exit(1)


def fetch_firms():
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{SOURCE}/{BBOX}/{DAYS}"
    )
    print(f"Загружаю FIRMS (key: {MAP_KEY[:6]}...)")
    print(f"URL: {url[:80]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read().decode("utf-8", errors="ignore")
    print(f"Получено байт: {len(data)}")
    return data


def parse_firms_csv(data):
    features = []
    reader = csv.DictReader(io.StringIO(data))
    for row in reader:
        try:
            lat = float(row.get("latitude") or 0)
            lng = float(row.get("longitude") or 0)
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue

            brightness = float(row.get("bright_ti4") or row.get("brightness") or 300)

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {
                    "brightness": brightness,
                    "satellite": row.get("satellite", ""),
                    "acq_date": row.get("acq_date", ""),
                    "acq_time": row.get("acq_time", ""),
                    "confidence": row.get("confidence", ""),
                    "frp": float(row.get("frp") or 0)
                }
            })
        except Exception:
            continue

    features.sort(key=lambda f: -f["properties"]["brightness"])
    return features[:MAX_RECORDS]


def main():
    try:
        data = fetch_firms()
        features = parse_firms_csv(data)
        print(f"Найдено пожаров: {len(features)}")

        output = {
            "type": "FeatureCollection",
            "generated": datetime.utcnow().isoformat() + "Z",
            "features": features
        }

        os.makedirs("data", exist_ok=True)
        with open("data/firms-fires.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)

        print("✅ Сохранено в data/firms-fires.json")

    except Exception as e:
        print(f"❌ Ошибка: {e}", file=sys.stderr)
        output = {
            "type": "FeatureCollection",
            "generated": datetime.utcnow().isoformat() + "Z",
            "features": []
        }
        os.makedirs("data", exist_ok=True)
        with open("data/firms-fires.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
