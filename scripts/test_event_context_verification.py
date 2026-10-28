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
