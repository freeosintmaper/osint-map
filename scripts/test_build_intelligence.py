#!/usr/bin/env python3
"""Offline tests for summaries and event-history generation."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_intelligence as intelligence


class IntelligencePipelineTests(unittest.TestCase):
    def make_event(self, event_id, event_type, location, date, source_type="telegram"):
        return {
            "id": event_id,
            "event_type": event_type,
            "location": location,
            "country": "UA",
            "date": date,
            "channel": "source_one",
            "source_type": source_type,
            "url": "https://example.org/" + str(event_id),
            "verification_status": "not_verified",
            "description": "Публічне повідомлення про подію",
        }

    def test_parser_reads_window_tg_data_object(self):
        event = self.make_event("1", "Military Strike", "Киев", "2026-10-31T10:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.js"
            path.write_text(
                "window.TG_DATA = " + json.dumps({"events": [event]}) + ";",
                encoding="utf-8",
            )
            payload = intelligence.parse_events_js(path)
        self.assertEqual(len(payload["events"]), 1)

    def test_parser_rejects_invalid_javascript_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.js"
            path.write_text("window.TG_DATA = not-json;", encoding="utf-8")
            with self.assertRaises(intelligence.IntelligenceError):
                intelligence.parse_events_js(path)

    def test_event_fingerprint_is_stable(self):
        event = self.make_event("1", "Military Strike", "Киев", "2026-10-31T10:08:00Z")
        same_hour = dict(event, date="2026-10-31T10:59:00Z")
        self.assertEqual(
            intelligence.event_fingerprint(event),
            intelligence.event_fingerprint(same_hour),
        )

    def test_daily_summary_counts_sources_and_corroboration_carefully(self):
        now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        events = [
            self.make_event("1", "Military Strike", "Киев", "2026-10-31T11:00:00Z"),
            self.make_event("2", "Air Raid Alert", "Харьков", "2026-10-31T10:00:00Z", "rss"),
        ]
        events[0]["verification_status"] = "corroborated"
        summary = intelligence.build_summary(
            events, now - timedelta(hours=24), now, [], set(), "last_24_hours"
        )
        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["event_type_counts"]["Military Strike"], 1)
        self.assertEqual(summary["source_type_counts"], {"rss": 1, "telegram": 1})
        self.assertEqual(summary["corroborated_event_count"], 1)
        self.assertEqual(summary["not_verified_event_count"], 1)
        self.assertIn("не", summary["method_note"].lower())

    def test_history_is_versioned_and_has_added_removed_items(self):
        added = self.make_event("new", "Military Strike", "Киев", "2026-10-31T11:00:00Z")
        removed = self.make_event("old", "Military Operation", "Одесса", "2026-10-31T09:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "event-history"
            index = history / "index.json"
            with (
                mock.patch.object(intelligence, "HISTORY_DIR", history),
                mock.patch.object(intelligence, "HISTORY_INDEX", index),
            ):
                intelligence.update_daily_history(
                    "2026-10-31", "2026-10-31T12:00:00Z", [added], [removed], 12
                )
                record = json.loads((history / "2026-10-31.json").read_text(encoding="utf-8"))
                manifest = json.loads(index.read_text(encoding="utf-8"))
        self.assertEqual(len(record["events_added"]), 1)
        self.assertEqual(len(record["events_removed"]), 1)
        self.assertEqual(record["current_event_count"], 12)
        self.assertEqual(manifest["days"][0]["date"], "2026-10-31")

    def test_daily_history_cancels_events_added_then_removed(self):
        event = self.make_event("temporary", "Military Strike", "Киев", "2026-10-31T11:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "event-history"
            index = history / "index.json"
            with (
                mock.patch.object(intelligence, "HISTORY_DIR", history),
                mock.patch.object(intelligence, "HISTORY_INDEX", index),
            ):
                intelligence.update_daily_history(
                    "2026-10-31", "2026-10-31T12:00:00Z", [event], [], 1
                )
                intelligence.update_daily_history(
                    "2026-10-31", "2026-10-31T12:30:00Z", [], [event], 0
                )
                record = json.loads((history / "2026-10-31.json").read_text(encoding="utf-8"))
        self.assertEqual(record["events_added"], [])
        self.assertEqual(record["events_removed"], [])

    def test_daily_history_cancels_events_removed_then_restored(self):
        event = self.make_event("restored", "Military Strike", "Киев", "2026-10-31T11:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "event-history"
            index = history / "index.json"
            with (
                mock.patch.object(intelligence, "HISTORY_DIR", history),
                mock.patch.object(intelligence, "HISTORY_INDEX", index),
            ):
                intelligence.update_daily_history(
                    "2026-10-31", "2026-10-31T12:00:00Z", [], [event], 0
                )
                intelligence.update_daily_history(
                    "2026-10-31", "2026-10-31T12:30:00Z", [event], [], 1
                )
                record = json.loads((history / "2026-10-31.json").read_text(encoding="utf-8"))
        self.assertEqual(record["events_added"], [])
        self.assertEqual(record["events_removed"], [])

    def test_source_freshness_is_separate_from_endpoint_health(self):
        now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        sources = {
            "telegram_fresh": {
                "type": "telegram",
                "status": "ok",
                "latest_item_at": "2026-10-30T12:00:00Z",
            },
            "rss_stale": {
                "type": "rss",
                "status": "ok",
                "latest_item_at": "2026-10-26T12:00:00Z",
            },
            "telegram_unknown": {
                "type": "telegram",
                "status": "error",
                "last_success": "2026-10-31T10:00:00Z",
            },
        }
        freshness = intelligence.annotate_source_freshness(sources, now)
        self.assertEqual(
            freshness["status_counts"],
            {"fresh": 1, "stale": 1, "unknown": 1},
        )
        self.assertEqual(sources["telegram_fresh"]["freshness_status"], "fresh")
        self.assertEqual(sources["rss_stale"]["freshness_status"], "stale")
        self.assertEqual(sources["rss_stale"]["status"], "ok")
        self.assertEqual(sources["telegram_unknown"]["freshness_status"], "unknown")
        self.assertEqual(freshness["stale_sources"][0]["id"], "rss_stale")
        self.assertEqual(freshness["stale_sources"][0]["threshold_hours"], 96)

    def test_source_statistics_keep_publishers_distinct(self):
        events = [
            dict(self.make_event("1", "Military Strike", "Киев", "2026-10-31T10:00:00Z"),
                 sources=[{"channel": "telegram_a", "url": "https://example.org/a"}]),
            dict(self.make_event("2", "Military Strike", "Киев", "2026-10-31T10:10:00Z"),
                 source_type="rss", sources=[{"publisher": "Independent News", "channel": "rss_a"}]),
        ]
        counts = intelligence._source_counts(events)
        self.assertEqual(counts["telegram_a"], 1)
        self.assertEqual(counts["Independent News"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
