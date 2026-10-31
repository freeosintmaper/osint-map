#!/usr/bin/env python3
"""Fetch public RSS headlines as a separate, provenance-preserving event source.

Only headlines are stored in the public map dataset. Article summaries are used
transiently for conservative event/location matching and are not republished.
RSS events are never used to upgrade Telegram corroboration status.
"""
from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "source-registry.json"
RSS_DATA_PATH = ROOT / "data" / "rss-events.json"
SOURCE_HEALTH_PATH = ROOT / "data" / "source-health.json"
MAX_FEED_BYTES = 6 * 1024 * 1024
MAX_FEED_ITEMS = 120
MAX_AGE_DAYS = 7
TIMEOUT_SECONDS = 25

sys.path.insert(0, str(ROOT / "scripts"))
import parse_telegram as parser  # noqa: E402


class FeedError(RuntimeError):
    pass


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def strip_markup(value: Any) -> str:
    raw = html.unescape(str(value or ""))
    extractor = _TextExtractor()
    try:
        extractor.feed(raw)
        extractor.close()
        return extractor.text()
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", raw)).strip()


def _local_name(tag: str) -> str:
    return str(tag).split("}")[-1].split(":")[-1].lower()


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in list(node):
        if _local_name(child.tag) in names:
            if child.text:
                return child.text.strip()
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def _parse_published(value: str) -> str | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        return None


def _canonical_url(value: str) -> str:
    value = str(value or "").strip()
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.netloc:
            return ""
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    except ValueError:
        return ""


def parse_feed_items(xml_bytes: bytes) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom entries without depending on a third-party package."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise FeedError(f"Malformed RSS/Atom XML: {error}") from error

    nodes = [
        node for node in root.iter()
        if _local_name(node.tag) in {"item", "entry"}
    ]
    parsed: list[dict[str, str]] = []
    for node in nodes[:MAX_FEED_ITEMS]:
        title = strip_markup(_child_text(node, {"title"}))
        link = _child_text(node, {"link"})
        if not link:
            for child in list(node):
                if _local_name(child.tag) == "link":
                    rel = str(child.attrib.get("rel") or "alternate").lower()
                    if rel in {"alternate", ""} and child.attrib.get("href"):
                        link = child.attrib["href"]
                        break
        link = _canonical_url(link)
        published = _parse_published(_child_text(
            node, {"pubdate", "published", "updated", "date", "created"}
        ))
        summary = strip_markup(_child_text(
            node, {"description", "summary", "content", "encoded"}
        ))
        if title and link and published:
            parsed.append({
                "title": title[:500],
                "url": link,
                "date": published,
                "context": summary[:2500],
            })
    return parsed


def load_registry() -> list[dict[str, Any]]:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FeedError(f"Cannot load source registry: {error}") from error
    sources = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(sources, list):
        raise FeedError("Source registry has no sources array.")
    feeds = [s for s in sources if isinstance(s, dict) and s.get("type") == "rss" and s.get("enabled")]
    for source in feeds:
        if not source.get("id") or not source.get("publisher") or not _canonical_url(source.get("feed_url", "")):
            raise FeedError("RSS source registry contains an invalid or non-HTTPS feed.")
    return feeds


def fetch_feed(url: str) -> bytes:
    request = Request(url, headers={
        "User-Agent": "OSINT-Map/1.0 (+https://github.com/freeosintmaper/osint-map)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5",
    })
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_FEED_BYTES + 1)
    except HTTPError as error:
        raise FeedError(f"HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise FeedError(str(error)[:250]) from error
    if len(body) > MAX_FEED_BYTES:
        raise FeedError(f"Feed exceeds {MAX_FEED_BYTES} bytes.")
    return body


def _explicit_region(text: str):
    """Use region-centre fallback only when the region is explicitly in the lead."""
    lead = parser._primary_event_context(text)
    return parser._region_center_from_text(lead)


def _unique_city_locations(text: str) -> list[tuple[float, float, str, str]]:
    """Return only unambiguous settlements; homonyms without country context are skipped."""
    lead = parser._primary_event_context(text)
    if not parser.SETTLEMENTS_BY_NAME:
        parser.load_settlements()

    region = _explicit_region(lead)
    region_country = region[3] if region else None
    words = re.findall(r"[а-яёa-zа-їієґ0-9-]+", lead.lower())
    candidates: dict[str, tuple[float, float, str, str]] = {}

    # Check known aliases, but do not trust a default alias when a homonym exists.
    alias_matches, _ = parser._find_alias_matches(lead, "OSINT")
    for lat, lng, name, country in alias_matches:
        settlement_candidates = parser.SETTLEMENTS_BY_NAME.get(parser._normalize_context_text(name), [])
        countries = {item[2] for item in settlement_candidates}
        if region_country and country != region_country:
            continue
        if len(countries) > 1 and not region_country:
            continue
        candidates[name] = (float(lat), float(lng), str(name), str(country))

    # Match multi-word settlement names, but accept a name only if its country is unique.
    for size in (3, 2, 1):
        for index in range(len(words) - size + 1):
            phrase = " ".join(words[index:index + size])
            if len(phrase) < 5 or phrase in parser.ABBREVIATIONS or phrase in parser.STOP_SETTLEMENTS:
                continue
            if phrase not in parser.SETTLEMENTS_BY_NAME:
                continue
            if parser.is_military_term_context(lead, phrase):
                continue
            if parser.has_source_verb_near(lead, phrase, window=60):
                continue
            if not parser.has_event_pattern_near(lead, phrase, window=250):
                continue
            matches = parser.SETTLEMENTS_BY_NAME[phrase]
            if region_country:
                scoped = [item for item in matches if item[2] == region_country]
                if not scoped:
                    continue
                matches = scoped
            countries = {item[2] for item in matches}
            if len(countries) != 1:
                continue
            best = max(matches, key=lambda item: item[4])
            lat, lng, country, name, _population = best
            if name not in candidates:
                candidates[name] = (float(lat), float(lng), str(name), str(country))

    return list(candidates.values())[:parser.MAX_LOCATIONS_PER_POST]


def map_headline(source: dict[str, Any], item: dict[str, str]) -> list[dict[str, Any]]:
    """Map a title only when event type and settlement context are both explicit."""
    title = str(item.get("title") or "").strip()
    # Deliberately classify and geolocate from the headline alone. A broad
    # publisher summary may mention background locations unrelated to the event.
    event_type = parser.classify_event(title)
    if not event_type:
        return []

    locations: list[tuple[float, float, str, str]] = []
    region = _explicit_region(title)
    if region:
        locations = [(float(region[0]), float(region[1]), str(region[2]), str(region[3]))]
    else:
        locations = _unique_city_locations(title)
    if not locations:
        return []

    source_id = str(source["id"])
    publisher = str(source["publisher"])
    source_meta = {
        "channel": source_id,
        "source_type": "rss",
        "publisher": publisher,
        "url": item["url"],
        "date": item["date"],
    }
    event_id = "rss-" + hashlib.sha256((source_id + "|" + item["url"]).encode("utf-8")).hexdigest()[:18]
    result: list[dict[str, Any]] = []
    for lat, lng, location, country in locations:
        result.append({
            "id": event_id + "-" + hashlib.sha256(location.encode("utf-8")).hexdigest()[:6],
            "url": item["url"],
            "date": item["date"],
            "event_type": event_type,
            "location": location,
            "country": country,
            "lat": lat,
            "lng": lng,
            "coordinate_precision": "settlement_center",
            "confidence": "LOW",
            "description": title[:220],
            "channel": source_id,
            "source_type": "rss",
            "source_count": 1,
            "sources": [source_meta],
            "verification_status": "not_verified",
            "verification_sources": [],
            "verification_note": "RSS-заголовок классифицирован правилами и привязан к центру населённого пункта. Это не редакционная проверка и не независимое подтверждение.",
        })
    return result


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def update_source_health(source_id: str, entry: dict[str, Any]) -> None:
    payload = _load_json(SOURCE_HEALTH_PATH, {"sources": {}})
    health = payload.get("sources") if isinstance(payload, dict) else {}
    if not isinstance(health, dict):
        health = {}
    previous = dict(health.get(source_id) or {})
    previous.update(entry)
    previous["id"] = source_id
    previous["type"] = "rss"
    health[source_id] = previous
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": health,
        "method_note": "Health means endpoint fetch succeeded; it does not measure the truth or quality of published reports."
    }
    _atomic_json(SOURCE_HEALTH_PATH, payload)


def collect() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    old_payload = _load_json(RSS_DATA_PATH, {"events": []})
    old_events = old_payload.get("events", []) if isinstance(old_payload, dict) else []
    old_by_source: dict[str, list[dict[str, Any]]] = {}
    for event in old_events if isinstance(old_events, list) else []:
        if not isinstance(event, dict):
            continue
        source_id = str(event.get("channel") or "")
        old_by_source.setdefault(source_id, []).append(event)

    all_events: list[dict[str, Any]] = []
    feed_health: dict[str, Any] = {}
    feeds = load_registry()
    if not parser.SETTLEMENTS_BY_NAME:
        parser.load_settlements()

    for source in feeds:
        source_id = str(source["id"])
        attempted_at = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        previous_events = old_by_source.get(source_id, [])
        retained = []
        for event in previous_events:
            try:
                event_date = datetime.fromisoformat(str(event.get("date", "")).replace("Z", "+00:00"))
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=timezone.utc)
                if event_date >= cutoff:
                    retained.append(event)
            except (TypeError, ValueError):
                continue

        try:
            xml_bytes = fetch_feed(str(source["feed_url"]))
            items = parse_feed_items(xml_bytes)
            mapped: list[dict[str, Any]] = []
            for item in items:
                try:
                    item_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                except ValueError:
                    continue
                if item_date < cutoff or item_date > now + timedelta(hours=12):
                    continue
                mapped.extend(map_headline(source, item))
            # Keep older still-relevant cached feed items if the publisher's RSS window is short.
            by_url: dict[str, dict[str, Any]] = {}
            for event in retained + mapped:
                url = str(event.get("url") or "")
                if url:
                    by_url[url + "|" + str(event.get("location") or "")] = event
            source_events = list(by_url.values())
            feed_health[source_id] = {
                "status": "ok",
                "endpoint": source["feed_url"],
                "last_attempt": attempted_at,
                "last_success": attempted_at,
                "last_error": None,
                "items_seen": len(items),
                "events_mapped": len(mapped),
            }
            print(f"[{source_id}] fetched {len(items)} items; mapped {len(mapped)} event locations.")
        except FeedError as error:
            source_events = retained
            previous_health = _load_json(SOURCE_HEALTH_PATH, {}).get("sources", {}).get(source_id, {})
            feed_health[source_id] = {
                "status": "error",
                "endpoint": source["feed_url"],
                "last_attempt": attempted_at,
                "last_success": previous_health.get("last_success"),
                "last_error": str(error)[:300],
                "items_seen": previous_health.get("items_seen", 0),
                "events_mapped": len(source_events),
            }
            print(f"[{source_id}] feed unavailable: {error}; retained {len(source_events)} cached events.", file=sys.stderr)
        all_events.extend(source_events)
        update_source_health(source_id, feed_health[source_id])
        time.sleep(0.25)

    # URL + settlement is the stable key; separate publishers remain separate sources.
    unique: dict[str, dict[str, Any]] = {}
    for event in all_events:
        key = str(event.get("url") or "") + "|" + str(event.get("location") or "")
        if key and key != "|":
            unique[key] = event
    events = sorted(
        unique.values(),
        key=lambda event: str(event.get("date") or ""),
        reverse=True
    )[:600]
    generated_at = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "window_days": MAX_AGE_DAYS,
        "events": events,
        "feed_health": feed_health,
        "method_note": "RSS items are separate, unverified source records. Only the title is stored; the original publisher link is retained."
    }
    _atomic_json(RSS_DATA_PATH, payload)
    return payload


def main() -> int:
    parser_arg = argparse.ArgumentParser(description=__doc__)
    parser_arg.add_argument("--check", action="store_true", help="Validate registry and parse cached RSS data without network requests.")
    args = parser_arg.parse_args()
    try:
        if args.check:
            feeds = load_registry()
            cached = _load_json(RSS_DATA_PATH, {"events": []})
            if not isinstance(cached.get("events"), list):
                raise FeedError("Cached RSS data has an invalid events array.")
            print(f"Registry valid: {len(feeds)} RSS feeds; cached events: {len(cached['events'])}.")
        else:
            payload = collect()
            print(f"RSS pipeline complete: {len(payload['events'])} events retained.")
        return 0
    except FeedError as error:
        print(f"RSS pipeline error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
