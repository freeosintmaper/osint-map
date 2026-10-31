#!/usr/bin/env python3
"""Build compact, reproducible OSINT activity summaries and event change history."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENTS_JS = ROOT / "data" / "telegram-events.js"
RSS_JSON = ROOT / "data" / "rss-events.json"
SOURCE_HEALTH = ROOT / "data" / "source-health.json"
DAILY_JSON = ROOT / "data" / "daily-summary.json"
WEEKLY_JSON = ROOT / "data" / "weekly-summary.json"
INTELLIGENCE_JS = ROOT / "data" / "osint-intelligence.js"
HISTORY_DIR = ROOT / "data" / "event-history"
HISTORY_INDEX = HISTORY_DIR / "index.json"
HISTORY_RETENTION_DAYS = 90

METHOD_NOTE = (
    "Это автоматическая статистика публикаций из открытых источников, а не "
    "оценка интенсивности боевых действий, подтверждение фактов или вывод о контроле территории. "
    "Несколько публикаций могут ссылаться на один первоисточник."
)


class IntelligenceError(RuntimeError):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


CONTENT_FRESHNESS_THRESHOLDS_HOURS = {"telegram": 72, "rss": 96}


def annotate_source_freshness(
    sources: dict[str, Any], now: datetime
) -> dict[str, Any]:
    """Separate endpoint reachability from the age of the newest published item."""
    counts: Counter[str] = Counter()
    stale_sources: list[dict[str, Any]] = []
    for source_id, item in sources.items():
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("type") or "telegram").lower()
        threshold = float(
            item.get("freshness_threshold_hours")
            or CONTENT_FRESHNESS_THRESHOLDS_HOURS.get(source_type, 72)
        )
        latest_item = parse_datetime(item.get("latest_item_at"))
        if latest_item is None:
            status = "unknown"
            age_hours = None
        else:
            age_hours = max(0.0, (now - latest_item).total_seconds() / 3600)
            status = "stale" if age_hours > threshold else "fresh"

        item["freshness_status"] = status
        item["latest_item_age_hours"] = round(age_hours, 1) if age_hours is not None else None
        item["freshness_threshold_hours"] = threshold
        counts[status] += 1
        if status == "stale":
            stale_sources.append({
                "id": source_id,
                "type": source_type,
                "latest_item_at": item.get("latest_item_at"),
                "age_hours": round(age_hours, 1),
                "threshold_hours": threshold,
            })

    stale_sources.sort(key=lambda item: item["age_hours"], reverse=True)
    return {
        "status_counts": {
            "fresh": counts.get("fresh", 0),
            "stale": counts.get("stale", 0),
            "unknown": counts.get("unknown", 0),
        },
        "stale_sources": stale_sources,
        "thresholds_hours": CONTENT_FRESHNESS_THRESHOLDS_HOURS,
        "method_note": (
            "Freshness measures the age of the newest publication, not the reachability "
            "of the feed. Thresholds are conservative: Telegram 72h, RSS 96h. "
            "Unknown means no publication timestamp was available."
        ),
    }


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def parse_events_js(path: Path) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise IntelligenceError(f"Cannot read {path}: {error}") from error
    match = re.match(r"^\s*window\.TG_DATA\s*=\s*(\{.*\})\s*;?\s*$", source, re.DOTALL)
    if not match:
        raise IntelligenceError(f"{path} does not contain a valid window.TG_DATA object.")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise IntelligenceError(f"Invalid TG_DATA JSON: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise IntelligenceError("TG_DATA has no events array.")
    return payload


def normalized_text(value: Any) -> str:
    text = str(value or "").casefold().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def event_fingerprint(event: dict[str, Any]) -> str:
    """Stable key for comparing two parser snapshots; not a claim events are unique in reality."""
    source_urls = sorted({
        str(source.get("url") or "")
        for source in (event.get("sources") or [])
        if isinstance(source, dict) and source.get("url")
    })
    primary_url = str(event.get("url") or "")
    time = parse_datetime(event.get("date"))
    time_bucket = time.strftime("%Y-%m-%dT%H") if time else ""
    parts = [
        str(event.get("source_type") or "telegram"),
        str(event.get("country") or ""),
        normalized_text(event.get("location")),
        str(event.get("event_type") or ""),
        time_bucket,
        primary_url if primary_url else "|".join(source_urls),
        normalized_text(event.get("description")),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "date", "event_type", "location", "country", "lat", "lng",
        "coordinate_precision", "confidence", "description", "channel",
        "source_type", "source_count", "sources", "url",
        "verification_status", "verification_sources", "verification_note"
    )
    return {key: event.get(key) for key in keys if key in event}


def _filter_window(events: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    selected = []
    for event in events:
        event_time = parse_datetime(event.get("date"))
        if event_time and start <= event_time <= end:
            selected.append(event)
    return selected


def _event_type_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(e.get("event_type") or "Unknown") for e in events).items()))


def _country_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(e.get("country") or "Unknown") for e in events).items()))


def _location_counts(events: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    counts = Counter(
        (str(e.get("country") or ""), str(e.get("location") or ""))
        for e in events if e.get("location")
    )
    return [
        {"country": country, "location": location, "events": count}
        for (country, location), count in counts.most_common(limit)
    ]


def _source_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for event in events:
        sources = event.get("sources")
        if isinstance(sources, list) and sources:
            for source in sources:
                if isinstance(source, dict):
                    name = str(source.get("publisher") or source.get("channel") or "").strip()
                    if name:
                        counts[name] += 1
        else:
            for name in str(event.get("channel") or "").split(","):
                if name.strip():
                    counts[name.strip()] += 1
    return dict(counts.most_common(12))


def _activity_signals(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current_counts = Counter(str(e.get("event_type") or "Unknown") for e in current)
    previous_counts = Counter(str(e.get("event_type") or "Unknown") for e in previous)
    signals = []
    for event_type in sorted(set(current_counts) | set(previous_counts)):
        now_count = current_counts[event_type]
        previous_count = previous_counts[event_type]
        delta = now_count - previous_count
        if delta >= 5 and now_count >= max(8, previous_count * 1.5):
            signals.append({
                "event_type": event_type,
                "current_period": now_count,
                "previous_period": previous_count,
                "delta": delta,
                "label": "Повышенная публикационная активность"
            })
    return signals


def build_summary(
    events: list[dict[str, Any]],
    start: datetime,
    end: datetime,
    previous_events: list[dict[str, Any]],
    added_fingerprints: set[str],
    name: str
) -> dict[str, Any]:
    selected = _filter_window(events, start, end)
    previous_start = start - (end - start)
    previous_end = start - timedelta(seconds=1)
    previous_selected = _filter_window(previous_events, previous_start, previous_end)
    corroborated = sum(1 for e in selected if e.get("verification_status") == "corroborated")
    source_types = Counter(str(e.get("source_type") or "telegram") for e in selected)
    return {
        "period": name,
        "generated_at": iso(now_utc()),
        "window_start": iso(start),
        "window_end": iso(end),
        "event_count": len(selected),
        "new_since_previous_snapshot": sum(
            1 for e in selected if event_fingerprint(e) in added_fingerprints
        ),
        "event_type_counts": _event_type_counts(selected),
        "country_counts": _country_counts(selected),
        "top_locations": _location_counts(selected),
        "top_sources": _source_counts(selected),
        "source_type_counts": dict(sorted(source_types.items())),
        "corroborated_event_count": corroborated,
        "not_verified_event_count": len(selected) - corroborated,
        "publication_activity_signals": _activity_signals(selected, previous_selected),
        "method_note": METHOD_NOTE
    }


def update_daily_history(today: str, generated_at: str, added: list[dict[str, Any]], removed: list[dict[str, Any]], total: int) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = HISTORY_DIR / f"{today}.json"
    existing = load_json(path, {})
    existing_added = existing.get("events_added", []) if isinstance(existing, dict) else []
    existing_removed = existing.get("events_removed", []) if isinstance(existing, dict) else []
    added_map = {
        item.get("fingerprint"): item
        for item in existing_added if isinstance(item, dict) and item.get("fingerprint")
    }
    removed_map = {
        item.get("fingerprint"): item
        for item in existing_removed if isinstance(item, dict) and item.get("fingerprint")
    }
    # Track the net change relative to the start of the UTC day. An event
    # added and later removed (or removed and later restored) cancels out.
    for event in added:
        fp = event_fingerprint(event)
        if fp in removed_map:
            removed_map.pop(fp, None)
        else:
            added_map[fp] = {"fingerprint": fp, "event": _event_summary(event)}
    for event in removed:
        fp = event_fingerprint(event)
        if fp in added_map:
            added_map.pop(fp, None)
        else:
            removed_map[fp] = {"fingerprint": fp, "event": _event_summary(event)}
    record = {
        "date_utc": today,
        "generated_at": generated_at,
        "current_event_count": total,
        "events_added": list(added_map.values())[-500:],
        "events_removed": list(removed_map.values())[-500:],
        "method_note": "Изменения показывают разницу между автоматическими выгрузками, а не доказанное изменение обстановки."
    }
    atomic_json(path, record)

    index = load_json(HISTORY_INDEX, {"days": []})
    days = index.get("days", []) if isinstance(index, dict) else []
    by_date = {item.get("date"): item for item in days if isinstance(item, dict) and item.get("date")}
    by_date[today] = {
        "date": today,
        "events_added": len(record["events_added"]),
        "events_removed": len(record["events_removed"]),
        "current_event_count": total
    }
    retained = sorted(by_date.values(), key=lambda item: item["date"], reverse=True)[:HISTORY_RETENTION_DAYS]
    atomic_json(HISTORY_INDEX, {
        "generated_at": generated_at,
        "retention_days": HISTORY_RETENTION_DAYS,
        "days": retained
    })
    keep = {item["date"] for item in retained}
    for old_path in HISTORY_DIR.glob("20??-??-??.json"):
        if old_path.stem not in keep:
            try:
                old_path.unlink()
            except OSError:
                pass


def main() -> int:
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("--previous", type=Path, default=None, help="Previous telegram-events.js snapshot.")
    args = args_parser.parse_args()

    try:
        current_payload = parse_events_js(EVENTS_JS)
        current_telegram_events = [
            event for event in current_payload["events"]
            if isinstance(event, dict) and str(event.get("source_type") or "telegram") != "rss"
        ]
        rss_payload = load_json(RSS_JSON, {"events": []})
        rss_events = rss_payload.get("events", []) if isinstance(rss_payload, dict) else []
        if not isinstance(rss_events, list):
            raise IntelligenceError("rss-events.json has an invalid events array.")

        previous_events: list[dict[str, Any]] = []
        if args.previous and args.previous.exists():
            previous_payload = parse_events_js(args.previous)
            previous_events = [e for e in previous_payload["events"] if isinstance(e, dict)]

        combined: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for event in current_telegram_events + [e for e in rss_events if isinstance(e, dict)]:
            event_id = str(event.get("id") or event_fingerprint(event))
            key = str(event.get("source_type") or "telegram") + "|" + event_id
            if key in seen_ids:
                continue
            seen_ids.add(key)
            combined.append(event)
        combined.sort(key=lambda e: str(e.get("date") or ""), reverse=True)

        previous_fps = {event_fingerprint(e) for e in previous_events}
        current_fps = {event_fingerprint(e) for e in combined}
        added_events = [e for e in combined if event_fingerprint(e) not in previous_fps]
        removed_events = [e for e in previous_events if event_fingerprint(e) not in current_fps]
        added_fps = {event_fingerprint(e) for e in added_events}

        generated_at = iso(now_utc())
        now = now_utc()
        daily_start = now - timedelta(hours=24)
        weekly_start = now - timedelta(days=7)
        daily = build_summary(combined, daily_start, now, previous_events, added_fps, "last_24_hours")
        weekly = build_summary(combined, weekly_start, now, previous_events, added_fps, "last_7_days")
        daily["generated_at"] = generated_at
        weekly["generated_at"] = generated_at
        source_health = load_json(SOURCE_HEALTH, {"sources": {}})
        health_sources = source_health.get("sources", {}) if isinstance(source_health, dict) else {}
        health_status = Counter(
            str(item.get("status") or "unknown")
            for item in health_sources.values() if isinstance(item, dict)
        )
        freshness = annotate_source_freshness(health_sources, now)
        source_health["generated_at"] = generated_at
        source_health["sources"] = health_sources
        source_health["freshness"] = freshness
        atomic_json(SOURCE_HEALTH, source_health)
        health_summary = {
            "generated_at": source_health.get("generated_at") if isinstance(source_health, dict) else None,
            "total_sources": len(health_sources),
            "status_counts": dict(health_status),
            "freshness_counts": freshness["status_counts"],
            "stale_sources": freshness["stale_sources"],
            "freshness_method_note": freshness["method_note"],
            "freshness_thresholds_hours": freshness["thresholds_hours"],
            "sources": health_sources,
            "method_note": "Доступность endpoint не измеряет качество публикаций и независимость источников."
        }

        today = now.strftime("%Y-%m-%d")
        update_daily_history(today, generated_at, added_events, removed_events, len(combined))

        intelligence = {
            "generated_at": generated_at,
            "daily": daily,
            "weekly": weekly,
            "source_health": health_summary,
            "change_history_url": "./data/event-history/index.json",
            "method_note": METHOD_NOTE
        }
        atomic_json(DAILY_JSON, daily)
        atomic_json(WEEKLY_JSON, weekly)
        js = "window.OSINT_INTELLIGENCE = " + json.dumps(intelligence, ensure_ascii=False, separators=(",", ":")) + ";\n"
        atomic_write(INTELLIGENCE_JS, js)

        payload = {
            "generated_at": generated_at,
            "pipeline": "telegram+rss",
            "event_count": len(combined),
            "source_types": {
                "telegram": sum(1 for e in combined if str(e.get("source_type") or "telegram") == "telegram"),
                "rss": sum(1 for e in combined if str(e.get("source_type") or "") == "rss")
            },
            "daily_summary_url": "./data/daily-summary.json",
            "weekly_summary_url": "./data/weekly-summary.json",
            "events": combined
        }
        output = "window.TG_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
        atomic_write(EVENTS_JS, output)
        print(
            f"Intelligence pipeline: {len(combined)} events "
            f"(+{len(added_events)} / -{len(removed_events)} vs previous snapshot); "
            f"daily={daily['event_count']}, weekly={weekly['event_count']}."
        )
        return 0
    except IntelligenceError as error:
        print(f"Intelligence pipeline error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
