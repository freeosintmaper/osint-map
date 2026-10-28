import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import parse_telegram as parser


class EventContextAndVerificationTests(unittest.TestCase):
    def make_event(self, location, description, channel, date, lat, lng):
        return {
            "id": 1,
            "url": "https://t.me/" + channel + "/1",
            "date": date,
            "event_type": "Military Strike",
            "location": location,
            "country": "RU",
            "lat": lat,
            "lng": lng,
            "coordinate_precision": "settlement_center",
            "description": description,
            "channel": channel,
        }

    def test_secondary_supplier_city_is_not_the_event_location(self):
        text = (
            'В Тульской области загорелся химзавод "Азот" после атаки дронов\n\n'
            "Это предприятие обеспечивает кислотой завод им. Свердлова в Дзержинске."
        )
        lead = parser._primary_event_context(text)
        self.assertFalse(parser._location_mentioned_in_context("Дзержинск", lead))
        self.assertTrue(parser._location_mentioned_in_context("Дзержинск", text))

    def test_tula_region_is_mapped_to_region_centre_not_supplier_city(self):
        location = parser._region_center_from_text(
            'В Тульской области загорелся химзавод "Азот" после атаки дронов',
            "UA",
        )
        self.assertIsNotNone(location)
        self.assertEqual(location[2], "Тула")
        self.assertEqual(location[3], "RU")

    def test_context_only_city_is_replaced_by_corroborated_event_town(self):
        wrong = self.make_event(
            "Тула",
            'В Тульской области загорелся химзавод "Азот" после атаки дронов\n\n'
            "Это предприятие обеспечивает кислотой завод им. Свердлова в Дзержинске.",
            "uniannet",
            "2026-10-28T04:08:36+00:00",
            54.1961,
            37.6182,
        )
        corroborating = self.make_event(
            "Новомосковск",
            "У місті Новомосковськ Тульської області РФ безпілотники атакували "
            "хімзавод Азот, на підприємстві виникла пожежа.",
            "ukrpravda_news",
            "2026-10-28T07:10:15+00:00",
            54.01098,
            38.29084,
        )
        parser._correct_contextual_locations([wrong, corroborating])
        self.assertEqual(wrong["location"], "Новомосковск")
        self.assertAlmostEqual(wrong["lat"], 54.01098)
        self.assertAlmostEqual(wrong["lng"], 38.29084)
        self.assertEqual(wrong["coordinate_precision"], "settlement_center")
        self.assertEqual(wrong["location_resolution"], "context_corroborated_settlement")

    def test_same_named_city_uses_region_from_related_report(self):
        ambiguous = self.make_event(
            "Новомосковск",
            'Новомосковск местные жители сообщают об атаке и пожаре на АО «НАК Азот».',
            "exilenova_plus",
            "2026-10-28T03:54:32+00:00",
            48.62893,
            35.2589,
        )
        region_report = self.make_event(
            "Новомосковск",
            "Новомосковськ, Тульська область, атаковано хімічний завод «Азот», "
            "після атаки на підприємстві розпочалася пожежа.",
            "exilenova_plus",
            "2026-10-28T04:17:20+00:00",
            54.01098,
            38.29084,
        )
        ambiguous["country"] = "UA"
        region_report["country"] = "RU"
        parser._correct_contextual_locations([ambiguous, region_report])
        self.assertEqual(ambiguous["country"], "RU")
        self.assertAlmostEqual(ambiguous["lat"], 54.01098)
        self.assertAlmostEqual(ambiguous["lng"], 38.29084)
        self.assertEqual(ambiguous["location_resolution"], "context_corroborated_country")

    def test_follow_up_media_inherits_explicit_region_from_same_channel(self):
        follow_up = self.make_event(
            "Новомосковск",
            "Ещё кадры с Новомосковска после атаки этим утром.",
            "exilenova_plus",
            "2026-10-28T05:09:54+00:00",
            48.62893,
            35.2589,
        )
        region_report = self.make_event(
            "Новомосковск",
            "Новомосковськ, Тульська область, атаковано хімічний завод «Азот», "
            "після атаки на підприємстві розпочалася пожежа.",
            "exilenova_plus",
            "2026-10-28T04:17:20+00:00",
            54.01098,
            38.29084,
        )
        follow_up["country"] = "UA"
        region_report["country"] = "RU"
        parser._correct_contextual_locations([follow_up, region_report])
        self.assertEqual(follow_up["country"], "RU")
        self.assertAlmostEqual(follow_up["lat"], 54.01098)
        self.assertAlmostEqual(follow_up["lng"], 38.29084)
        self.assertEqual(follow_up["location_resolution"], "context_corroborated_country")

    def test_distinct_reports_from_different_channels_are_corroborated(self):
        first = self.make_event(
            "Новомосковск",
            'В Тульской области загорелся химзавод "Азот" после атаки дронов.',
            "uniannet",
            "2026-10-28T04:08:36+00:00",
            54.01098,
            38.29084,
        )
        second = self.make_event(
            "Новомосковск",
            "У місті Новомосковськ Тульської області безпілотники атакували "
            "хімзавод Азот, виникла пожежа.",
            "ukrpravda_news",
            "2026-10-28T07:10:15+00:00",
            54.01098,
            38.29084,
        )
        parser._apply_verification_status([first, second])
        self.assertEqual(first["verification_status"], "corroborated")
        self.assertIn("ukrpravda_news", first["verification_sources"])
        self.assertIn("uniannet", first["verification_sources"])

    def test_ambiguous_city_alias_respects_the_requested_country(self):
        key = "новомосковск"
        old_alias = parser.TRANSLIT_ALIASES.get(key)
        old_candidates = parser.SETTLEMENTS_BY_NAME.get(key)
        parser.TRANSLIT_ALIASES[key] = [48.62893, 35.2589, "Новомосковск", "UA"]
        parser.SETTLEMENTS_BY_NAME[key] = [
            (48.62893, 35.2589, "UA", "Новомосковск", 100000),
            (54.01098, 38.29084, "RU", "Новомосковск", 100000),
        ]
        try:
            locations = parser._geocode_llm_locations(
                [{
                    "name": "Новомосковск",
                    "country": "RU",
                    "confidence": 0.99,
                    "specific_place": None,
                    "evidence": None,
                }],
                "UA",
                "В Новомосковске Тульской области загорелся химзавод Азот.",
            )
            self.assertTrue(locations)
            self.assertEqual(locations[0][2], "Новомосковск")
            self.assertEqual(locations[0][3], "RU")
            self.assertAlmostEqual(locations[0][0], 54.01098)
            self.assertAlmostEqual(locations[0][1], 38.29084)
        finally:
            if old_alias is None:
                parser.TRANSLIT_ALIASES.pop(key, None)
            else:
                parser.TRANSLIT_ALIASES[key] = old_alias
            if old_candidates is None:
                parser.SETTLEMENTS_BY_NAME.pop(key, None)
            else:
                parser.SETTLEMENTS_BY_NAME[key] = old_candidates

    def test_verbatim_cross_posts_are_not_marked_verified(self):
        text = 'В Тульской области загорелся химзавод "Азот" после атаки дронов.'
        first = self.make_event(
            "Новомосковск", text, "channel_one",
            "2026-10-28T04:08:36+00:00", 54.01098, 38.29084,
        )
        second = self.make_event(
            "Новомосковск", text, "channel_two",
            "2026-10-28T04:15:00+00:00", 54.01098, 38.29084,
        )
        parser._apply_verification_status([first, second])
        self.assertEqual(first["verification_status"], "not_verified")
        self.assertEqual(second["verification_status"], "not_verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
