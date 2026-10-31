#!/usr/bin/env python3
"""Offline regression tests for the author-zones backup."""
import json
import tempfile
import unittest
from pathlib import Path

from backup_author_zones import (
    BackupError,
    build_feature_collection,
    extract_supabase_credentials,
    validate_geometry,
    write_backup,
)

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[30.0, 50.0], [31.0, 50.0], [31.0, 51.0], [30.0, 50.0]]],
}


class AuthorZonesBackupTests(unittest.TestCase):
    def test_extracts_public_supabase_config(self):
        html = "var SB_URL = 'https://example.supabase.co'; var SB_KEY = 'public-key';"
        self.assertEqual(
            extract_supabase_credentials(html),
            ("https://example.supabase.co", "public-key"),
        )

    def test_builds_feature_collection(self):
        rows = [
            {"id": 2, "category": "grey", "geometry": POLYGON},
            {"id": 1, "category": "ukraine", "geometry": POLYGON},
        ]
        collection = build_feature_collection(rows)
        self.assertEqual(collection["type"], "FeatureCollection")
        self.assertEqual(
            [feature["properties"]["id"] for feature in collection["features"]],
            [1, 2],
        )
        self.assertEqual(collection["features"][0]["geometry"], POLYGON)

    def test_rejects_empty_source(self):
        with self.assertRaises(BackupError):
            build_feature_collection([])

    def test_rejects_invalid_geometry(self):
        with self.assertRaises(BackupError):
            validate_geometry({"type": "Polygon", "coordinates": []})

    def test_rejects_unclosed_ring(self):
        invalid = {
            "type": "Polygon",
            "coordinates": [[[30, 50], [31, 50], [31, 51], [30, 51]]],
        }
        with self.assertRaises(BackupError):
            validate_geometry(invalid)

    def test_backup_is_idempotent_and_preserves_history(self):
        collection = build_feature_collection([
            {"id": 1, "category": "grey", "geometry": POLYGON}
        ])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(write_backup(collection, root))
            latest = root / "data" / "author-zones.geojson"
            history = list((root / "data" / "author-zones-history").glob("*.geojson"))
            self.assertTrue(latest.exists())
            self.assertEqual(len(history), 1)
            self.assertFalse(write_backup(collection, root))
            self.assertEqual(len(list((root / "data" / "author-zones-history").glob("*.geojson"))), 1)
            self.assertEqual(json.loads(latest.read_text(encoding="utf-8")), collection)


if __name__ == "__main__":
    unittest.main()
