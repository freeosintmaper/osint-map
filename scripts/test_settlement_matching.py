import json
import os
import sys
import unittest
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.dirname(__file__))
import parse_telegram as parser


class SettlementMatchingTests(unittest.TestCase):
    def setUp(self):
        self.old_index = parser.SETTLEMENTS_BY_NAME
        self.old_audit = parser.GEOCODE_AUDIT.copy()
        parser.SETTLEMENTS_BY_NAME = {}

    def tearDown(self):
        parser.SETTLEMENTS_BY_NAME = self.old_index
        parser.GEOCODE_AUDIT.clear()
        parser.GEOCODE_AUDIT.update(self.old_audit)

    def test_small_ua_and_ru_settlements_are_not_removed_by_population(self):
        rows = [
            {"name": "Малое Поле", "lat": 48.1, "lng": 36.1, "country": "UA", "population": 350},
            {"name": "Тихая Долина", "lat": 51.1, "lng": 35.1, "country": "RU", "population": 420},
        ]
        source = "window.SETTLEMENTS = " + json.dumps(rows, ensure_ascii=False) + ";"
        with patch("os.path.exists", return_value=True), patch("builtins.open", mock_open(read_data=source)):
            parser.load_settlements()

        self.assertIn("малое поле", parser.SETTLEMENTS_BY_NAME)
        self.assertIn("тихая долина", parser.SETTLEMENTS_BY_NAME)
        self.assertEqual(parser.SETTLEMENTS_BY_NAME["малое поле"][0][4], 350)
        self.assertEqual(parser.SETTLEMENTS_BY_NAME["тихая долина"][0][4], 420)

    def test_rejected_alias_does_not_block_another_real_settlement_match(self):
        key = "долинском"
        old = parser.SETTLEMENTS_BY_NAME.get(key)
        parser.SETTLEMENTS_BY_NAME[key] = [
            (48.1, 36.1, "UA", "Долинское", 2500)
        ]
        try:
            text = (
                "В Киеве состоялось заседание. "
                + "Нейтральное описание решения без географических данных. " * 7
                + "В Долинском произошёл взрыв."
            )
            locations = parser.find_all_locations(text, "UA")
            self.assertTrue(locations)
            self.assertEqual(locations[0][2], "Долинское")
            self.assertEqual(locations[0][3], "UA")
            self.assertGreater(
                parser.GEOCODE_AUDIT["alias_rejected_city_search_continued"], 0
            )
        finally:
            if old is None:
                parser.SETTLEMENTS_BY_NAME.pop(key, None)
            else:
                parser.SETTLEMENTS_BY_NAME[key] = old

    def test_osint_homonym_uses_explicit_region_country(self):
        key = "новомосковск"
        old = parser.SETTLEMENTS_BY_NAME.get(key)
        parser.SETTLEMENTS_BY_NAME[key] = [
            (48.62893, 35.2589, "UA", "Новомосковск", 100000),
            (54.01098, 38.29084, "RU", "Новомосковск", 100000),
        ]
        try:
            text = "Новомосковск Тульской области. Произошёл взрыв."
            locations = parser._find_city_matches(text, "OSINT")
            self.assertTrue(locations)
            self.assertEqual(locations[0][4], "RU")
            self.assertAlmostEqual(locations[0][2], 54.01098)
            self.assertAlmostEqual(locations[0][3], 38.29084)
        finally:
            if old is None:
                parser.SETTLEMENTS_BY_NAME.pop(key, None)
            else:
                parser.SETTLEMENTS_BY_NAME[key] = old

    def test_osint_homonym_without_country_context_is_not_guessed(self):
        key = "новомосковск"
        old = parser.SETTLEMENTS_BY_NAME.get(key)
        parser.SETTLEMENTS_BY_NAME[key] = [
            (48.62893, 35.2589, "UA", "Новомосковск", 100000),
            (54.01098, 38.29084, "RU", "Новомосковск", 100000),
        ]
        try:
            locations = parser._find_city_matches(
                "Новомосковск. Произошёл взрыв.", "OSINT"
            )
            self.assertEqual(locations, [])
        finally:
            if old is None:
                parser.SETTLEMENTS_BY_NAME.pop(key, None)
            else:
                parser.SETTLEMENTS_BY_NAME[key] = old


if __name__ == "__main__":
    unittest.main()
