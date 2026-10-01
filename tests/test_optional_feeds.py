"""Opt-in feeds (config-only FeedSpecs) parse their synthetic format fixtures offline."""

import asyncio
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news import feed_adapter
from news.optional_feeds import (
    BANGKOK_POST_TECH,
    OPTIONAL_FEEDS,
    TECHCRUNCH,
    THAIGER_BUSINESS,
    BangkokPostTechScraper,
    TechCrunchScraper,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from run_feeds import FEEDS, select_feeds  # noqa: E402


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class OptionalFeedTests(unittest.TestCase):
    def test_bangkok_post_tech_uses_bangkok_time_and_drops_invalid_entries(self):
        _, rows = feed_adapter.parse_feed(BANGKOK_POST_TECH, (FIXTURES / "bangkok_post_tech.xml").read_bytes())
        self.assertEqual([row["url"] for row in rows], [
            "https://www.bangkokpost.com/tech/1000001/sample-tech-headline-one",
            "https://www.bangkokpost.com/tech/1000002/sample-tech-headline-two",
        ])
        self.assertEqual(rows[0]["published_at"], "2026-08-25T06:45:00Z")
        self.assertEqual(rows[1]["published_at"], "2026-08-25T02:15:00Z")
        self.assertEqual(rows[0]["section"], "technology")
        self.assertEqual(rows[0]["summary"], "Sample summary one.")
        self.assertEqual(rows[0]["source"], "Bangkok Post Tech")
        self.assertEqual(rows[0]["source_url"], "https://www.bangkokpost.com/rss/data/tech.xml")

    def test_wordpress_feeds_keep_author_topics_guid_and_https_on_site_links(self):
        _, rows = feed_adapter.parse_feed(
            THAIGER_BUSINESS, (FIXTURES / "wordpress_thaiger_business.xml").read_bytes()
        )
        self.assertEqual(len(rows), 2)  # plain-HTTP link dropped
        self.assertEqual(rows[0]["article_id"], "https://thethaiger.com/?p=100001")
        self.assertEqual(rows[0]["author"], "Sample Author")
        self.assertEqual(rows[0]["topics"], "Business News,Economy")
        self.assertEqual(rows[0]["summary"], "Sample summary one…")
        self.assertEqual(rows[1]["url"], "https://thethaiger.com/news/business/sample-business-headline-two")
        self.assertEqual(rows[1]["published_at"], "2026-08-25T01:00:00Z")
        self.assertEqual(rows[0]["updated_at"], "")

        _, rows = feed_adapter.parse_feed(TECHCRUNCH, (FIXTURES / "wordpress_techcrunch.xml").read_bytes())
        self.assertEqual([row["title"] for row in rows], ["Sample startup headline & more", "Subdomain link is kept"])
        self.assertEqual(rows[0]["topics"], "Startups,AI")
        self.assertEqual(rows[0]["url"], "https://techcrunch.com/2026/08/25/sample-startup-headline")

    def test_feed_url_policy(self):
        self.assertEqual(
            feed_adapter.normalize_feed_url(TECHCRUNCH, "https://techcrunch.com/feed/"), "https://techcrunch.com/feed"
        )
        for spec, bad in (
            (TECHCRUNCH, "https://techcrunch.com.evil.example/feed/"),
            (TECHCRUNCH, "http://techcrunch.com/feed/"),
            (BANGKOK_POST_TECH, "https://www.bangkokpost.com/rss/data/business.xml"),
            (THAIGER_BUSINESS, "https://thethaiger.com/news/feed"),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    feed_adapter.normalize_feed_url(spec, bad)

    def test_every_optional_feed_rejects_empty_and_off_site_feeds(self):
        off_site = (FIXTURES / "matichon_feed.xml").read_bytes()
        for _name, cls in OPTIONAL_FEEDS:
            with self.subTest(feed=cls.spec.key):
                with self.assertRaises(ValueError):
                    feed_adapter.parse_feed(cls.spec, b"")
                with self.assertRaisesRegex(ValueError, "contract-compliant"):
                    feed_adapter.parse_feed(cls.spec, off_site)

    def test_run_writes_raw_snapshot_and_history_under_the_feed_key(self):
        raw = (FIXTURES / "bangkok_post_tech.xml").read_bytes()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("news.http.httpx.get", return_value=FakeResponse(raw)):
                result = asyncio.run(BangkokPostTechScraper(limit=10, output_dir=temp_dir).run())
            out = Path(temp_dir)
            self.assertEqual(result[0]["source"], "bangkok_post_tech")
            self.assertEqual(result[0]["count"], 2)
            self.assertTrue((out / "bangkok_post_tech_raw.xml").exists())
            with (out / "bangkok_post_tech.csv").open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BANGKOK_POST_TECH.snapshot_fields)
                self.assertEqual(len(list(reader)), 2)
            self.assertTrue((out / "bangkok_post_tech_history.csv").exists())

    def test_generated_classes_are_named_and_validate_limits(self):
        self.assertEqual(TechCrunchScraper.__name__, "TechCrunchScraper")
        self.assertEqual(TechCrunchScraper.__module__, "news.optional_feeds")
        with self.assertRaises(ValueError):
            TechCrunchScraper(limit=0)


class FeedSelectionTests(unittest.TestCase):
    def test_default_roster_excludes_optional_feeds(self):
        self.assertEqual(select_feeds(None), FEEDS)
        default_names = {name for name, _ in FEEDS}
        self.assertFalse(default_names & {name for name, _ in OPTIONAL_FEEDS})

    def test_named_feeds_are_selected_once_in_order(self):
        selected = select_feeds(["techcrunch_tech", "matichon_news", "techcrunch_tech"])
        self.assertEqual([name for name, _ in selected], ["techcrunch_tech", "matichon_news"])
        with self.assertRaisesRegex(ValueError, "unknown feed"):
            select_feeds(["techsauce"])


if __name__ == "__main__":
    unittest.main()
