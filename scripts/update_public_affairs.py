#!/usr/bin/env python3
"""Collect non-military public-affairs headlines for a separate, non-geospatial page.

Only headline metadata and source links are published. This feed is deliberately
kept separate from the conflict-event map: it never creates coordinates or map
markers and never modifies data/rss-events.json or Telegram event data.
"""
from __future__ import annotations

import email.utils
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "public-affairs-news.json"
MAX_FEED_BYTES = 4 * 1024 * 1024
MAX_FEED_ITEMS = 100
MAX_AGE_DAYS = 7
MAX_OUTPUT_ITEMS = 180
TIMEOUT_SECONDS = 20

FEEDS: list[dict[str, Any]] = [
    {
        "id": "eu_commission",
        "publisher": "Европейская комиссия",
        "feed_url": "https://ec.europa.eu/newsroom/comm/feed?item_type_id=930&lang=en&orderby=item_date",
        "allowed_hosts": ["ec.europa.eu"],
        "default_category": "diplomacy",
    },
    {
        "id": "european_parliament",
        "publisher": "Европейский парламент",
        "feed_url": "https://www.europarl.europa.eu/rss/doc/press-releases/en.xml",
        "allowed_hosts": ["www.europarl.europa.eu", "europarl.europa.eu"],
        "default_category": "diplomacy",
    },
    {
        "id": "eurostat",
        "publisher": "Eurostat",
        "feed_url": "https://ec.europa.eu/eurostat/cache/RSS/rss_estat_news.xml",
        "allowed_hosts": ["ec.europa.eu"],
        "default_category": "economy",
    },
    {
        "id": "ecb",
        "publisher": "Европейский центральный банк",
        "feed_url": "https://www.ecb.europa.eu/rss/press.html",
        "allowed_hosts": ["www.ecb.europa.eu", "ecb.europa.eu"],
        "default_category": "economy",
    },
    {
        "id": "who",
        "publisher": "Всемирная организация здравоохранения",
        "feed_url": "https://www.who.int/rss-feeds/news-english.xml",
        "allowed_hosts": ["www.who.int", "who.int"],
        "default_category": "humanitarian",
    },
    {
        "id": "un_sdg",
        "publisher": "Новости ООН — устойчивое развитие",
        "feed_url": "https://news.un.org/feed/subscribe/en/news/topic/sdgs/feed/rss.xml",
        "allowed_hosts": ["news.un.org"],
        "default_category": "humanitarian",
    },
    {
        "id": "un_global",
        "publisher": "Новости ООН",
        "feed_url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "allowed_hosts": ["news.un.org"],
        "default_category": "humanitarian",
    },
]

CATEGORIES = {"diplomacy", "economy", "humanitarian"}

# Keep this board non-operational. Headlines about armed activity are omitted,
# not reclassified or mapped. This is a conservative filter and may exclude
# some otherwise relevant articles; the original publisher feeds remain linked.
EXCLUDED_RE = re.compile(
    r"\b(?:war|armed conflict|military|missile|drones?|airstrikes?|air raids?|"
    r"shelling|bomb(?:ing|ed)?|battlefields?|frontlines?|invasions?|offensives?|"
    r"troops?|weapons?|combat|army|navy|artillery|soldiers?|hostilities|"
    r"terror(?:ism|ist)|attacks?|attacked)\b"
    r"|войн\w*|военн\w*|воен\w*|обстрел\w*|ракет\w*|дрон\w*|шахед\w*|"
    r"взрыв\w*|бомб\w*|фронт\w*|боев\w*|воєн\w*|армі\w*|безпілот\w*|"
    r"збройн\w*|артилер\w*|наступ\w*|атак\w*|удар\w*|конфлікт\w*|конфликт\w*",
    re.IGNORECASE,
)

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("diplomacy", (
        "summit", "agreement", "treaty", "parliament", "election", "government",
        "commission", "council", "diplom", "foreign affairs", "international",
        "cooperation", "legislation", "regulation", "human rights", "policy",
        "переговор", "саммит", "соглашен", "парламент", "выбор", "правительств",
        "комисс", "совет", "диплом", "международ", "сотруднич", "закон",
    )),
    ("economy", (
        "econom", "inflation", "interest rate", "trade", "investment", "employment",
        "jobs", "gdp", "budget", "finance", "financial", "market", "prices", "debt",
        "growth", "tax", "banking", "monetary", "export", "import", "business",
        "эконом", "инфляц", "процентн", "торгов", "инвестиц", "занятост", "рабочих мест",
        "бюджет", "финанс", "рынок", "цены", "долг", "рост", "налог", "банк",
    )),
    ("humanitarian", (
        "health", "healthcare", "education", "climate", "food", "nutrition", "hunger",
        "children", "housing", "refugees", "migration", "disaster", "water", "sanitation",
        "poverty", "inequality", "vaccine", "disease", "pollution", "biodiversity",
        "public health", "здравоохран", "здоров", "образован", "климат", "продоволь",
        "питани", "голод", "дет", "жиль", "бежен", "миграц", "катастроф", "вода",
        "бедност", "неравенств", "вакцин", "заболеван", "эколог",
    )),
]


class FeedError(RuntimeError):
    """Raised when a feed cannot be safely fetched or parsed."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def clean_text(value: Any) -> str:
    raw = html.unescape(str(value or ""))
    parser = _TextExtractor()
    try:
        parser.feed(raw)
        parser.close()
        return parser.text()
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", raw)).strip()


def local_name(tag: str) -> str:
    return str(tag).split("}")[-1].split(":")[-1].lower()


def child_text(node: ET.Element, names: set[str]) -> str:
    for child in list(node):
        if local_name(child.tag) in names:
            text = "".join(child.itertext()).strip()
            if text:
                return text
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def parse_date(value: str) -> str | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_article_url(value: str, allowed_hosts: list[str]) -> str:
    try:
        parts = urlsplit(str(value or "").strip())
        host = (parts.hostname or "").lower()
        if parts.scheme.lower() != "https" or host not in {h.lower() for h in allowed_hosts}:
            return ""
        if parts.username or parts.password:
            return ""
        return parts._replace(fragment="").geturl()
    except ValueError:
        return ""


def parse_feed_items(xml_bytes: bytes, allowed_hosts: list[str]) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom; retain headline metadata only."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise FeedError(f"Malformed RSS/Atom XML: {error}") from error

    entries = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
    parsed: list[dict[str, str]] = []
    for node in entries[:MAX_FEED_ITEMS]:
        title = clean_text(child_text(node, {"title"}))[:240]
        raw_link = child_text(node, {"link"})
        if not raw_link:
            for child in list(node):
                if local_name(child.tag) == "link":
                    rel = str(child.attrib.get("rel") or "alternate").lower()
                    if rel in {"alternate", ""} and child.attrib.get("href"):
                        raw_link = child.attrib["href"]
                        break
        link = safe_article_url(raw_link, allowed_hosts)
        published = parse_date(child_text(
            node, {"pubdate", "published", "updated", "date", "issued", "created"}
        ))
        if title and link and published:
            parsed.append({"title": title, "url": link, "date": published})
    return parsed


def classify_category(title: str, fallback: str) -> str:
    lowered = title.casefold()
    for category, terms in CATEGORY_RULES:
        if any(term in lowered for term in terms):
            return category
    return fallback if fallback in CATEGORIES else "humanitarian"


def make_item(source: dict[str, Any], parsed: dict[str, str]) -> dict[str, str] | None:
    title = re.sub(r"\s+", " ", str(parsed.get("title") or "")).strip()
    if not title or EXCLUDED_RE.search(title):
        return None
    category = classify_category(title, str(source.get("default_category") or "humanitarian"))
    if category not in CATEGORIES:
        return None
    source_id = str(source["id"])
    url = str(parsed["url"])
    item_id = hashlib.sha256((source_id + "|" + url).encode("utf-8")).hexdigest()[:20]
    return {
        "id": item_id,
        "title": title[:240],
        "url": url,
        "date": str(parsed["date"]),
        "publisher": str(source["publisher"]),
        "source_id": source_id,
        "category": category,
    }


def fetch_feed(source: dict[str, Any]) -> bytes:
    request = Request(str(source["feed_url"]), headers={
        "User-Agent": "OSINT-Map-Public-Affairs/1.0 (+https://github.com/freeosintmaper/osint-map)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
    })
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            final_host = (urlsplit(response.geturl()).hostname or "").lower()
            allowed = {str(host).lower() for host in source["allowed_hosts"]}
            if final_host not in allowed:
                raise FeedError("Feed redirected outside its publisher host allowlist.")
            body = response.read(MAX_FEED_BYTES + 1)
    except HTTPError as error:
        raise FeedError(f"HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise FeedError(str(error)[:200]) from error
    if len(body) > MAX_FEED_BYTES:
        raise FeedError("Feed response exceeded the size limit.")
    return body


def collect(
    now: datetime | None = None,
    feeds: list[dict[str, Any]] | None = None,
    fetcher: Callable[[dict[str, Any]], bytes] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    active_feeds = feeds if feeds is not None else FEEDS
    fetcher = fetcher or fetch_feed

    unique: dict[str, dict[str, str]] = {}
    health: list[dict[str, Any]] = []
    successful_feeds = 0

    for source in active_feeds:
        source_status: dict[str, Any] = {
            "id": str(source["id"]),
            "publisher": str(source["publisher"]),
            "status": "error",
            "items_seen": 0,
            "items_included": 0,
            "latest_item_at": None,
        }
        try:
            raw = fetcher(source)
            parsed_items = parse_feed_items(raw, list(source["allowed_hosts"]))
            successful_feeds += 1
            source_status["status"] = "ok"
            source_status["items_seen"] = len(parsed_items)
            for parsed in parsed_items:
                try:
                    published = datetime.fromisoformat(parsed["date"].replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                if published < cutoff or published > now + timedelta(hours=12):
                    continue
                item = make_item(source, parsed)
                if not item:
                    continue
                unique[item["url"]] = item
                source_status["items_included"] += 1
                if not source_status["latest_item_at"] or item["date"] > source_status["latest_item_at"]:
                    source_status["latest_item_at"] = item["date"]
        except (FeedError, KeyError, TypeError, ValueError) as error:
            source_status["error"] = str(error)[:200]
            print(f"[{source['id']}] feed skipped: {error}", file=sys.stderr)
        health.append(source_status)

    if active_feeds and successful_feeds == 0:
        raise FeedError("All public-affairs feeds failed; existing output was not changed.")

    items = sorted(unique.values(), key=lambda item: item["date"], reverse=True)[:MAX_OUTPUT_ITEMS]
    category_counts = {category: sum(1 for item in items if item["category"] == category)
                       for category in sorted(CATEGORIES)}
    return {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window_days": MAX_AGE_DAYS,
        "items": items,
        "category_counts": category_counts,
        "source_health": health,
        "method_note": (
            "Отдельная негеографическая лента невоенных новостей. Сохраняются только "
            "заголовок, дата, издатель и ссылка на первоисточник; координаты и маркеры "
            "не создаются. Военные и связанные с боевыми действиями заголовки отбрасываются."
        ),
    }


def write_payload(payload: dict[str, Any], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=str(output_path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
        Path(temp_name).replace(output_path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    try:
        payload = collect()
        write_payload(payload)
    except FeedError as error:
        print(f"Public-affairs update failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Updated public-affairs feed: {len(payload['items'])} headlines "
        f"from {sum(1 for source in payload['source_health'] if source['status'] == 'ok')} feeds."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
