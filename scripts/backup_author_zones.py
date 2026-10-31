#!/usr/bin/env python3
"""Create a validated, versioned read-only backup of the author's map zones.

The Supabase anon key is intentionally public and is already embedded in index.html
for browser-side reads. This script only performs GET requests and never writes to
Supabase. Empty or malformed responses are rejected so they cannot replace a good
backup.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
LATEST_PATH = ROOT / "data" / "author-zones.geojson"
HISTORY_DIR = ROOT / "data" / "author-zones-history"
PAGE_SIZE = 500
TIMEOUT_SECONDS = 30


class BackupError(RuntimeError):
    """Raised when source data cannot safely be backed up."""


def extract_supabase_credentials(html: str) -> tuple[str, str]:
    """Read the public Supabase URL and anon key from the frontend config."""
    def extract(name: str) -> str | None:
        match = re.search(
            rf"\bvar\s+{re.escape(name)}\s*=\s*(['\"])(.*?)\1\s*;",
            html,
            re.DOTALL,
        )
        return match.group(2).strip() if match else None

    url = os.environ.get("SUPABASE_URL") or extract("SB_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or extract("SB_KEY")
    if not url or not key:
        raise BackupError(
            "Supabase URL / anon key not found in index.html or environment."
        )
    return url.rstrip("/"), key


def _valid_position(position: Any) -> bool:
    if not isinstance(position, list) or len(position) < 2:
        return False
    try:
        longitude, latitude = float(position[0]), float(position[1])
    except (TypeError, ValueError, OverflowError):
        return False
    return (
        math.isfinite(longitude)
        and math.isfinite(latitude)
        and -180 <= longitude <= 180
        and -90 <= latitude <= 90
    )


def _validate_ring(ring: Any) -> bool:
    if not isinstance(ring, list) or len(ring) < 4:
        return False
    if not all(_valid_position(position) for position in ring):
        return False
    first, last = ring[0], ring[-1]
    return float(first[0]) == float(last[0]) and float(first[1]) == float(last[1])


def validate_geometry(geometry: Any) -> None:
    if not isinstance(geometry, dict):
        raise BackupError("A zone has no valid GeoJSON geometry object.")
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        valid = (
            isinstance(coordinates, list)
            and len(coordinates) > 0
            and all(_validate_ring(ring) for ring in coordinates)
        )
    elif geometry_type == "MultiPolygon":
        valid = (
            isinstance(coordinates, list)
            and len(coordinates) > 0
            and all(
                isinstance(polygon, list)
                and len(polygon) > 0
                and all(_validate_ring(ring) for ring in polygon)
                for polygon in coordinates
            )
        )
    else:
        valid = False
    if not valid:
        raise BackupError(
            f"Invalid or unsupported zone geometry: {geometry_type!r}."
        )


def build_feature_collection(rows: Any) -> dict[str, Any]:
    """Convert database rows into the stable subset consumed by the map."""
    if not isinstance(rows, list):
        raise BackupError("Supabase response is not a JSON array.")
    if not rows:
        raise BackupError(
            "Supabase returned zero author zones; refusing to overwrite the last backup."
        )

    features: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BackupError(f"Zone row #{index + 1} is not an object.")
        zone_id = row.get("id")
        category = row.get("category")
        geometry = row.get("geometry")
        if zone_id is None or isinstance(zone_id, (dict, list, bool)):
            raise BackupError(f"Zone row #{index + 1} has no valid id.")
        if not isinstance(category, str) or not category.strip():
            raise BackupError(f"Zone row #{index + 1} has no category.")
        key = str(zone_id)
        if key in seen_ids:
            raise BackupError(f"Duplicate zone id: {key}.")
        seen_ids.add(key)
        validate_geometry(geometry)
        features.append({
            "type": "Feature",
            "properties": {"id": zone_id, "category": category},
            "geometry": geometry,
        })

    features.sort(key=lambda feature: str(feature["properties"]["id"]))
    return {"type": "FeatureCollection", "features": features}


def fetch_rows(supabase_url: str, anon_key: str) -> list[dict[str, Any]]:
    """Read every row through the public, RLS-protected PostgREST endpoint."""
    endpoint = f"{supabase_url}/rest/v1/control_zones?{urlencode({'select': 'id,category,geometry', 'order': 'id.asc'})}"
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        request = Request(
            endpoint,
            headers={
                "apikey": anon_key,
                "Authorization": f"Bearer {anon_key}",
                "Accept": "application/json",
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + PAGE_SIZE - 1}",
                "User-Agent": "OSINT-Map-author-zones-backup/1.0",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = response.read()
        except HTTPError as error:
            raise BackupError(
                f"Supabase read failed with HTTP {error.code} ({error.reason})."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BackupError(f"Supabase read failed: {error}.") from error

        try:
            page = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BackupError("Supabase returned invalid JSON.") from error
        if not isinstance(page, list):
            raise BackupError("Supabase response is not a JSON array.")
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return rows


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def write_backup(collection: dict[str, Any], root: Path = ROOT) -> bool:
    """Write latest + immutable content-addressed history only when data changes."""
    latest_path = root / "data" / "author-zones.geojson"
    history_dir = root / "data" / "author-zones-history"
    content = (
        json.dumps(collection, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    previous = latest_path.read_bytes() if latest_path.exists() else None
    if previous == content:
        print(f"Author zones unchanged ({len(collection['features'])} zones); no commit needed.")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    history_path = history_dir / f"{timestamp}-{digest[:12]}.geojson"
    _atomic_write(latest_path, content)
    _atomic_write(history_path, content)
    print(
        f"Backed up {len(collection['features'])} author zones; "
        f"sha256={digest}; history={history_path.relative_to(root)}"
    )
    return True


def main() -> int:
    try:
        if not INDEX_HTML.exists():
            raise BackupError("index.html is missing; cannot read public Supabase config.")
        html = INDEX_HTML.read_text(encoding="utf-8")
        supabase_url, anon_key = extract_supabase_credentials(html)
        rows = fetch_rows(supabase_url, anon_key)
        collection = build_feature_collection(rows)
        write_backup(collection)
        return 0
    except BackupError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
