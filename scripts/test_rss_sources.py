#!/usr/bin/env python3
"""Offline tests for the modular RSS adapter."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_rss_sources as rss
import parse_telegram as parser


class RssSourceTests(unittest.TestCase):
    def test_registry_contains_telegram_sources_and_modular_rss_sources(self):
        feeds = rss.load_registry()
        self.assertEqual(len(parser.CHANNELS), 26)
        self.assertEqual(len(feeds), 5)
        self.assertTrue(all(feed["feed_url"].startswith("https://") for feed in feeds))
        registry_ids = {feed["id"] for feed in feeds}
        self.assertIn("rss_suspilne", registry_ids)
        self.assertIn("rss_bbc_ukrainian", registry_ids)

    def test_latest_feed_publication_timestamp_is_tracked(self):
        items = [
            {"date": "2026-10-30T10:00:00Z"},
            {"date": "2026-10-31T09:15:00Z"},
            {"date": "2026-10-29T20:00:00Z"},
        ]
        self.assertEqual(
            rss._latest_published_at(items),
            "2026-10-31T09:15:00Z",
        )
        self.assertIsNone(rss._latest_published_at([]))

    def test_rss_items_are_parsed_without_publishing_full_summary(self):
        sample = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><item>
          <title><![CDATA[У Дніпрі повідомили про наслідки атаки БПЛА]]></title>
          <link>https://example.org/news/123?utm_source=rss#top</link>
          <pubDate>Sat, 31 Oct 2026 10:00:00 GMT</pubDate>
          <description><![CDATA[<p>Подробный текст статьи, который не должен публиковаться в данных карты.</p>]]></description>
        </item></channel></rss>""".encode("utf-8")
        items = rss.parse_feed_items(sample)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "У Дніпрі повідомили про наслідки атаки БПЛА")
        self.assertEqual(items[0]["url"], "https://example.org/news/123?utm_source=rss")
        self.assertIn("Подробный текст", items[0]["context"])

    def test_atom_feed_is_supported(self):
        sample = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Article title</title>
            <link rel="alternate" href="https://example.org/article/1"/>
            <updated>2026-10-31T09:00:00Z</updated>
            <summary>Brief context</summary>
          </entry>
        </feed>"""
        items = rss.parse_feed_items(sample)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://example.org/article/1")
        self.assertEqual(items[0]["date"], "2026-10-31T09:00:00Z")

    def test_non_https_or_missing_link_items_are_dropped(self):
        sample = b"""<rss><channel>
        <item><title>Unsafe link</title><link>http://example.org/a</link><pubDate>Sat, 31 Oct 2026 10:00:00 GMT</pubDate></item>
        <item><title>Missing date</title><link>https://example.org/b</link></item>
        </channel></rss>"""
        self.assertEqual(rss.parse_feed_items(sample), [])

    def test_current_feed_article_replaces_old_cached_locations(self):
        url = "https://example.org/news/multi-place"
        retained = [
            {"url": url, "location": "Киев", "id": "old-kyiv"},
            {"url": url, "location": "Днепр", "id": "old-dnipro"},
            {"url": "https://example.org/news/older", "location": "Одесса", "id": "older"},
        ]
        mapped = [
            {"url": url, "location": "Харьков", "id": "new-kharkiv"},
        ]
        events = rss.merge_feed_events(retained, mapped, {url})
        self.assertEqual(
            {(event["url"], event["location"]) for event in events},
            {
                (url, "Харьков"),
                ("https://example.org/news/older", "Одесса"),
            },
        )
        self.assertNotIn("old-kyiv", {event["id"] for event in events})
        self.assertNotIn("old-dnipro", {event["id"] for event in events})

    def test_current_feed_article_with_no_new_location_drops_old_markers(self):
        url = "https://example.org/news/multi-place"
        retained = [
            {"url": url, "location": "Киев", "id": "old-kyiv"},
            {"url": url, "location": "Днепр", "id": "old-dnipro"},
        ]
        self.assertEqual(rss.merge_feed_events(retained, [], {url}), [])

    def test_malformed_xml_raises_feed_error(self):
        with self.assertRaises(rss.FeedError):
            rss.parse_feed_items(b"<rss><channel>")

    def test_rss_event_keeps_provenance_and_is_not_verified(self):
        source = {"id": "rss_test", "publisher": "Test newsroom", "type": "rss"}
        item = {
            "title": "Атака БПЛА на Тульскую область",
            "context": "",
            "url": "https://example.org/news/1",
            "date": "2026-10-31T10:00:00Z",
        }
        with mock.patch.object(parser, "classify_event", return_value="Military Strike"), \
             mock.patch.object(rss, "_explicit_region", return_value=(54.1961, 37.6182, "Тула", "RU")):
            events = rss.map_headline(source, item)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["source_type"], "rss")
        self.assertEqual(event["source_count"], 1)
        self.assertEqual(event["sources"][0]["publisher"], "Test newsroom")
        self.assertEqual(event["url"], item["url"])
        self.assertEqual(event["verification_status"], "not_verified")
        self.assertEqual(event["confidence"], "LOW")
        self.assertNotIn("context", event)
        self.assertEqual(event["coordinate_precision"], "settlement_center")

    def test_locations_in_secondary_sentence_do_not_inherit_event_context(self):
        source = {"id": "rss_test", "publisher": "Test newsroom", "type": "rss"}
        title = (
            "Вибухи на Полтавщині і в Харкові. "
            "Перебої з водою та світлом у Києві і в Дніпрі"
        )
        item = {
            "title": title,
            "context": "",
            "url": "https://example.org/news/multi-place",
            "date": "2026-10-31T10:00:00Z",
        }
        # Fixture includes inflected city forms as they appear in the headline.
        settlements = {
            "харкові": [(49.9935, 36.2304, "UA", "Харьков", 100000)],
            "києві": [(50.4501, 30.5234, "UA", "Киев", 100000)],
            "дніпрі": [(48.4647, 35.0462, "UA", "Днепр", 100000)],
        }
        with mock.patch.object(parser, "SETTLEMENTS_BY_NAME", settlements):
            events = rss.map_headline(source, item)

        self.assertEqual({event["location"] for event in events}, {"Полтава", "Харьков"})
        self.assertNotIn("Киев", {event["location"] for event in events})
        self.assertNotIn("Днепр", {event["location"] for event in events})
        self.assertTrue(all(event["verification_status"] == "not_verified" for event in events))

    def test_non_event_headline_is_not_added(self):
        source = {"id": "rss_test", "publisher": "Test newsroom"}
        item = {
            "title": "Sports results for the weekend",
            "context": "",
            "url": "https://example.org/sport",
            "date": "2026-10-31T10:00:00Z",
        }
        with mock.patch.object(parser, "classify_event", return_value=None):
            self.assertEqual(rss.map_headline(source, item), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
