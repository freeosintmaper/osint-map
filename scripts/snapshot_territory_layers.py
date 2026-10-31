#!/usr/bin/env python3
"""Record compact, reproducible references to upstream territorial-layer snapshots."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "data" / "territory-history" / "index.json"
RETENTION_DAYS = 90
TIMEOUT_SECONDS = 30
USER_AGENT = "OSINT-Map-Territory-History/1.0 (+https://github.com/freeosintmaper/osint-map)"


class SnapshotError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def request_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        raise SnapshotError(f"GitHub API HTTP {error.code}: {url}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SnapshotError(f"GitHub API unavailable: {error}") from error
    if len(raw) > 8 * 1024 * 1024:
        raise SnapshotError("GitHub API response exceeded 8 MiB safety limit")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotError(f"Invalid GitHub API JSON: {error}") from error


def _latest_commit(repository: str, path: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"path": path, "per_page": 1})
    payload = request_json(f"https://api.github.com/repos/{repository}/commits?{query}")
    if not isinstance(payload, list) or not payload:
        raise SnapshotError(f"No upstream commit found for {repository}/{path}")
    commit = payload[0]
    if not isinstance(commit, dict) or not commit.get("sha"):
        raise SnapshotError(f"Malformed commit response for {repository}/{path}")
    return commit


def fetch_deepstate_snapshot() -> dict[str, Any]:
    repository = "cyterat/deepstate-map-data"
    path = "deepstate-map-data.geojson.gz"
    commit = _latest_commit(repository, path)
    sha = str(commit["sha"])
    commit_data = commit.get("commit") or {}
    committer = commit_data.get("committer") or {}
    commit_date = str(committer.get("date") or "")
    raw_url = f"https://raw.githubusercontent.com/{repository}/{sha}/{path}"
    return {
        "provider": "DeepState",
        "status": "ok",
        "snapshot_date": commit_date[:10] if len(commit_date) >= 10 else None,
        "revision": sha,
        "upstream_commit_sha": sha,
        "upstream_commit_date": commit_date or None,
        "upstream_commit_url": str(commit.get("html_url") or f"https://github.com/{repository}/commit/{sha}"),
        "source_path": path,
        "source_url": raw_url,
        "archive_size_bytes": None,
        "archive_blob_sha": None,
    }


def parse_owl_archive_date(filename: str) -> date | None:
    match = re.fullmatch(r"(\d{2})(\d{2})(\d{2})_0601\.kmz", filename)
    if not match:
        return None
    yy, month, day = (int(part) for part in match.groups())
    try:
        return date(2000 + yy, month, day)
    except ValueError:
        return None


def fetch_project_owl_snapshot(today: date | None = None) -> dict[str, Any]:
    today = today or utc_now().date()
    repository = "owlmaps/UAControlMapBackups"
    last_error: Exception | None = None

    # At year boundaries the current-year folder may not yet contain an archive.
    for year in (today.year, today.year - 1, today.year - 2):
        folder = str(year)
        try:
            commit = _latest_commit(repository, folder)
            commit_sha = str(commit["sha"])
            query = urllib.parse.urlencode({"ref": commit_sha})
            entries = request_json(
                f"https://api.github.com/repos/{repository}/contents/{folder}?{query}"
            )
            if not isinstance(entries, list):
                raise SnapshotError(f"Malformed Project Owl directory listing for {folder}")
            candidates = []
            for item in entries:
                if not isinstance(item, dict) or item.get("type") != "file":
                    continue
                filename = str(item.get("name") or "")
                archive_date = parse_owl_archive_date(filename)
                if archive_date and archive_date.year == year and archive_date <= today:
                    candidates.append((archive_date, item))
            if not candidates:
                continue

            archive_date, item = max(candidates, key=lambda pair: pair[0])
            filename = str(item["name"])
            path = f"{folder}/{filename}"
            raw_url = f"https://raw.githubusercontent.com/{repository}/{commit_sha}/{path}"
            return {
                "provider": "Project Owl",
                "status": "ok",
                "snapshot_date": archive_date.isoformat(),
                "revision": str(item.get("sha") or commit_sha),
                "upstream_commit_sha": commit_sha,
                "upstream_commit_date": str((commit.get("commit") or {}).get("committer", {}).get("date") or "") or None,
                "upstream_commit_url": str(commit.get("html_url") or f"https://github.com/{repository}/commit/{commit_sha}"),
                "source_path": path,
                "source_url": raw_url,
                "archive_size_bytes": item.get("size"),
                "archive_blob_sha": item.get("sha"),
            }
        except SnapshotError as error:
            last_error = error
            continue

    if last_error:
        raise SnapshotError(f"Project Owl snapshot unavailable: {last_error}") from last_error
    raise SnapshotError("No dated Project Owl KMZ archive found in the last three year folders")


def _last_successful_source(
    snapshots: list[dict[str, Any]], source_id: str, before_date: str
) -> dict[str, Any] | None:
    eligible = sorted(
        (
            item for item in snapshots
            if isinstance(item, dict)
            and str(item.get("date") or "") < before_date
            and isinstance(item.get("sources"), dict)
            and isinstance(item["sources"].get(source_id), dict)
            and item["sources"][source_id].get("status") == "ok"
        ),
        key=lambda item: str(item.get("date") or ""),
        reverse=True,
    )
    return eligible[0]["sources"][source_id] if eligible else None


def build_daily_snapshot(
    snapshot_date: str,
    generated_at: str,
    successful_sources: dict[str, dict[str, Any]],
    errors: dict[str, str],
    previous_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    for source_id, source in successful_sources.items():
        previous = _last_successful_source(previous_snapshots, source_id, snapshot_date)
        revision = str(source.get("revision") or "")
        previous_revision = str(previous.get("revision") or "") if previous else ""
        change_status = "baseline" if not previous else (
            "unchanged" if revision and revision == previous_revision else "changed"
        )
        sources[source_id] = {**source, "change_status": change_status}

    for source_id, message in errors.items():
        sources[source_id] = {
            "provider": "DeepState" if source_id == "deepstate" else "Project Owl",
            "status": "error",
            "error": str(message)[:500],
        }

    return {
        "date": snapshot_date,
        "generated_at": generated_at,
        "sources": sources,
        "method_note": (
            "Это журнал версий и ссылок на исходные наборы, а не независимая оценка контроля территории. "
            "Геометрии остаются в репозиториях первоисточников; ссылки закреплены на конкретные версии."
        ),
    }


def upsert_daily_snapshot(
    index: dict[str, Any],
    snapshot: dict[str, Any],
    retention_days: int = RETENTION_DAYS,
) -> dict[str, Any]:
    existing = index.get("snapshots") if isinstance(index, dict) else []
    if not isinstance(existing, list):
        existing = []
    by_date = {
        str(item.get("date")): item
        for item in existing
        if isinstance(item, dict) and item.get("date")
    }
    today = str(snapshot["date"])
    previous_today = by_date.get(today, {})
    merged_sources = dict(previous_today.get("sources") or {})
    merged_sources.update(snapshot.get("sources") or {})
    merged = {**previous_today, **snapshot, "sources": merged_sources}
    by_date[today] = merged
    snapshots = sorted(by_date.values(), key=lambda item: str(item["date"]), reverse=True)[:retention_days]
    return {
        "schema_version": 1,
        "generated_at": snapshot["generated_at"],
        "retention_days": retention_days,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "method_note": (
            "Сохраняются даты и закреплённые ссылки на версии открытых картографических источников. "
            "Файлы геометрии не дублируются в этом репозитории."
        ),
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def main() -> int:
    now = utc_now()
    today = now.date().isoformat()
    generated_at = iso(now)
    existing = {}
    try:
        existing = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            existing = {}
    except (OSError, ValueError):
        existing = {}
    previous_snapshots = existing.get("snapshots", [])
    if not isinstance(previous_snapshots, list):
        previous_snapshots = []

    successful: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for source_id, fetcher in (
        ("deepstate", fetch_deepstate_snapshot),
        ("project_owl", fetch_project_owl_snapshot),
    ):
        try:
            successful[source_id] = fetcher()
            print(f"[{source_id}] snapshot {successful[source_id].get('snapshot_date')} revision={successful[source_id].get('revision')}")
        except SnapshotError as error:
            errors[source_id] = str(error)
            print(f"[{source_id}] unavailable: {error}", file=sys.stderr)

    if not successful:
        print("No territorial source snapshot could be recorded; previous history preserved.", file=sys.stderr)
        return 1

    daily = build_daily_snapshot(today, generated_at, successful, errors, previous_snapshots)
    updated = upsert_daily_snapshot(existing, daily)
    atomic_json(HISTORY_PATH, updated)
    print(
        f"Territorial history updated: {updated['snapshot_count']} daily records; "
        f"sources ok={len(successful)}, errors={len(errors)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
