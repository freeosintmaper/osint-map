import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_public_affairs as news


class PublicAffairsFeedTests(unittest.TestCase):
    def test_feed_registry_uses_https_and_explicit_hosts(self):
        self.assertGreaterEqual(len(news.FEEDS), 6)
        for feed in news.FEEDS:
            self.assertTrue(feed["feed_url"].startswith("https://"))
            self.assertTrue(feed["allowed_hosts"])
            self.assertIn(feed["default_category"], news.CATEGORIES)

    def test_rss_parser_keeps_headline_metadata_and_checks_publisher_host(self):
        sample = b"""<rss version="2.0"><channel><item>
          <title>European Commission presents a new housing policy plan</title>
          <link>https://ec.europa.eu/news/housing-policy</link>
          <pubDate>Sat, 28 Nov 2026 10:00:00 GMT</pubDate>
          <description>This description is intentionally not copied into the output.</description>
        </item><item>
          <title>Untrusted redirect target</title>
          <link>https://example.org/news/1</link>
          <pubDate>Sat, 28 Nov 2026 10:00:00 GMT</pubDate>
        </item></channel></rss>"""
        parsed = news.parse_feed_items(sample, ["ec.europa.eu"])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "European Commission presents a new housing policy plan")
        self.assertEqual(parsed[0]["url"], "https://ec.europa.eu/news/housing-policy")
        self.assertNotIn("description", parsed[0])
        self.assertNotIn("context", parsed[0])

    def test_atom_parser_accepts_alternate_link(self):
        sample = b"""<feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>WHO announces a public health initiative</title>
            <link rel="alternate" href="https://www.who.int/news/health-initiative"/>
            <updated>2026-11-28T10:00:00Z</updated>
          </entry>
        </feed>"""
        parsed = news.parse_feed_items(sample, ["www.who.int"])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["url"], "https://www.who.int/news/health-initiative")
        self.assertEqual(parsed[0]["date"], "2026-11-28T10:00:00Z")

    def test_military_and_armed_activity_headlines_are_excluded(self):
        self.assertIsNone(news.make_item(
            news.FEEDS[0],
            {
                "title": "Military strike reported after overnight drone attack",
                "url": "https://ec.europa.eu/news/1",
                "date": "2026-11-28T10:00:00Z",
            },
        ))
        self.assertIsNone(news.make_item(
            news.FEEDS[0],
            {
                "title": "В регионе сообщили о ракетном ударе",
                "url": "https://ec.europa.eu/news/2",
                "date": "2026-11-28T10:00:00Z",
            },
        ))

    def test_non_military_categories_are_assigned(self):
        self.assertEqual(news.classify_category(
            "European leaders sign a new cooperation agreement", "economy"
        ), "diplomacy")
        self.assertEqual(news.classify_category(
            "Eurostat reports inflation and household price trends", "diplomacy"
        ), "economy")
        self.assertEqual(news.classify_category(
            "WHO announces new vaccination and public health guidance", "economy"
        ), "humanitarian")

    def test_collect_keeps_separate_non_geospatial_items(self):
        source = {
            "id": "test_source",
            "publisher": "Test publisher",
            "allowed_hosts": ["example.org"],
            "default_category": "economy",
        }
        xml = b"""<rss><channel>
          <item><title>New trade and investment report published</title>
          <link>https://example.org/news/trade</link>
          <pubDate>Sat, 28 Nov 2026 10:00:00 GMT</pubDate></item>
          <item><title>Military attack reported in the region</title>
          <link>https://example.org/news/attack</link>
          <pubDate>Sat, 28 Nov 2026 10:15:00 GMT</pubDate></item>
        </channel></rss>"""
        payload = news.collect(
            now=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc),
            feeds=[source],
            fetcher=lambda _source: xml,
        )
        self.assertEqual(len(payload["items"]), 1)
        item = payload["items"][0]
        self.assertEqual(item["category"], "economy")
        self.assertEqual(item["publisher"], "Test publisher")
        self.assertFalse({"lat", "lng", "location", "coordinates"} & set(item))
        self.assertEqual(payload["source_health"][0]["status"], "ok")

    def test_all_failed_feeds_raise_and_do_not_create_empty_snapshot(self):
        def fail(_source):
            raise news.FeedError("network unavailable")

        with self.assertRaises(news.FeedError):
            news.collect(
                now=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc),
                feeds=[news.FEEDS[0]],
                fetcher=fail,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
