"""Shared feed helpers and per-adapter malformed-feed error paths (offline)."""

from __future__ import annotations

import unittest
from zoneinfo import ZoneInfo

import feedparser

from news import feed_common
from news import matichon_scraper, notebookspec_scraper, thai_business_scraper, thai_tech_scraper

RSS_NO_UPDATED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>A</title><link>https://example.com/a</link>
<pubDate>Tue, 25 Aug 2026 08:30:00 +0000</pubDate>
<category>x</category><category>x</category><category>y</category></item>
</channel></rss>"""

ATOM_WITH_UPDATED = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>T</title>
<entry><title>A</title><link href="https://example.com/a"/><id>a</id>
<published>2026-08-25T08:30:00Z</published><updated>2026-08-26T09:00:00Z</updated></entry></feed>"""


class FeedCommonTests(unittest.TestCase):
    def test_updated_at_is_empty_when_feed_has_no_update_time(self):
        entry = feedparser.parse(RSS_NO_UPDATED).entries[0]
        self.assertEqual(feed_common.published_at(entry), "2026-08-25T08:30:00Z")
        self.assertEqual(feed_common.updated_at(entry), "")

    def test_updated_at_reads_real_update_time(self):
        entry = feedparser.parse(ATOM_WITH_UPDATED).entries[0]
        self.assertEqual(feed_common.updated_at(entry), "2026-08-26T09:00:00Z")

    def test_naive_timestamps_use_the_source_timezone(self):
        bangkok = ZoneInfo("Asia/Bangkok")
        self.assertEqual(feed_common.parse_timestamp("2026-08-25T08:00:00", bangkok), "2026-08-25T01:00:00Z")
        self.assertEqual(feed_common.parse_timestamp("2026-08-25T08:00:00"), "2026-08-25T08:00:00Z")
        self.assertEqual(feed_common.parse_timestamp("not a date"), "")
        self.assertEqual(feed_common.parse_timestamp(None), "")

    def test_tag_terms_deduplicates(self):
        entry = feedparser.parse(RSS_NO_UPDATED).entries[0]
        self.assertEqual(feed_common.tag_terms(entry), "x,y")

    def test_clean_text_strips_markup_and_limits(self):
        self.assertEqual(feed_common.clean_text("<p>a &amp;  <b>b</b></p>", 100), "a & b")
        self.assertEqual(feed_common.clean_text("abcdef", 3), "abc")


class MalformedFeedTests(unittest.TestCase):
    ADAPTERS = (matichon_scraper, notebookspec_scraper, thai_business_scraper, thai_tech_scraper)

    def test_every_adapter_rejects_empty_and_garbage_feeds(self):
        for module in self.ADAPTERS:
            for raw in (b"", b"<html><body>not a feed</body></html>", b"<rss><channel></channel></rss>"):
                with self.subTest(module=module.__name__, raw=raw[:20]):
                    with self.assertRaises(ValueError):
                        module.parse_feed(raw, module.FEED_URL)

    def test_every_adapter_rejects_feeds_with_only_off_site_entries(self):
        for module in self.ADAPTERS:
            with self.subTest(module=module.__name__):
                with self.assertRaisesRegex(ValueError, "contract-compliant"):
                    module.parse_feed(RSS_NO_UPDATED, module.FEED_URL)


if __name__ == "__main__":
    unittest.main()
