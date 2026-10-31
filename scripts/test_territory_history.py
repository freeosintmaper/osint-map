#!/usr/bin/env python3
"""Offline tests for the territorial-source history manifest."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snapshot_territory_layers as history


class TerritorialHistoryTests(unittest.TestCase):
    def test_parse_owl_archive_date(self):
        self.assertEqual(history.parse_owl_archive_date("261031_0601.kmz").isoformat(), "2026-10-31")
        self.assertIsNone(history.parse_owl_archive_date("261332_0601.kmz"))
        self.assertIsNone(history.parse_owl_archive_date("readme.txt"))

    def test_daily_snapshot_marks_sources_changed_or_unchanged(self):
        previous = [{
            "date": "2026-10-30",
            "sources": {
                "deepstate": {"status": "ok", "revision": "deepstate-1"},
                "project_owl": {"status": "ok", "revision": "owl-1"},
            },
        }]
        current = history.build_daily_snapshot(
            "2026-10-31",
            "2026-10-31T06:30:00Z",
            {
                "deepstate": {"provider": "DeepState", "status": "ok", "revision": "deepstate-1"},
                "project_owl": {"provider": "Project Owl", "status": "ok", "revision": "owl-2"},
            },
            {},
            previous,
        )
        self.assertEqual(current["sources"]["deepstate"]["change_status"], "unchanged")
        self.assertEqual(current["sources"]["project_owl"]["change_status"], "changed")

    def test_first_snapshot_is_marked_as_baseline(self):
        current = history.build_daily_snapshot(
            "2026-10-31",
            "2026-10-31T06:30:00Z",
            {"deepstate": {"provider": "DeepState", "status": "ok", "revision": "first"}},
            {},
            [],
        )
        self.assertEqual(current["sources"]["deepstate"]["change_status"], "baseline")

    def test_upsert_replaces_same_day_and_retains_only_latest_days(self):
        index = {"snapshots": [
            {"date": "2026-10-30", "sources": {"deepstate": {"status": "ok", "revision": "a"}}},
            {"date": "2026-10-29", "sources": {"deepstate": {"status": "ok", "revision": "b"}}},
        ]}
        same_day = {
            "date": "2026-10-30",
            "generated_at": "2026-10-30T07:00:00Z",
            "sources": {"project_owl": {"status": "ok", "revision": "owl"}},
        }
        result = history.upsert_daily_snapshot(index, same_day, retention_days=2)
        self.assertEqual(result["snapshot_count"], 2)
        self.assertEqual(len(result["snapshots"]), 2)
        self.assertEqual(
            set(result["snapshots"][0]["sources"]),
            {"deepstate", "project_owl"},
        )
        self.assertEqual(result["snapshots"][0]["date"], "2026-10-30")
        self.assertEqual(result["snapshots"][1]["date"], "2026-10-29")

    def test_source_fetch_error_does_not_erase_successful_source(self):
        current = history.build_daily_snapshot(
            "2026-10-31",
            "2026-10-31T06:30:00Z",
            {"deepstate": {"provider": "DeepState", "status": "ok", "revision": "ds"}},
            {"project_owl": "upstream timeout"},
            [],
        )
        self.assertEqual(current["sources"]["deepstate"]["status"], "ok")
        self.assertEqual(current["sources"]["project_owl"]["status"], "error")
        self.assertIn("timeout", current["sources"]["project_owl"]["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
