"""Offline contract tests for the news.v1 lake/API boundary."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from news_data import config
from news_data import api, store


LAKE_HELPERS = store.product_store_available()
NEEDS_LAKE = unittest.skipUnless(
    LAKE_HELPERS,
    "parent data_lake helpers not found; set SOLO_EMPIRE_ROOT to a Solo Empire checkout",
)


class NewsDataApiTests(unittest.TestCase):
    @NEEDS_LAKE
    def test_news_item_preserves_attribution_and_normalizes_headline(self) -> None:
        item = store.news_item_from_bronze(
        {
            "event_time": "2026-09-08T00:00:00Z",
            "source_record_id": "Demo Publisher|article-001",
            "ingest_run_id": "run-001",
            "raw_object_key": "landing/source=book-news-scraping/batch-001/payload.csv",
            "payload_json": json.dumps(
                {
                    "id": "Demo Publisher|article-001",
                    "source": "Demo Publisher",
                    "article_id": "article-001",
                    "title": "Example headline",
                    "url": "https://publisher.example/news/article-001",
                    "source_url": "https://publisher.example/feed",
                    "captured_at": "2026-09-08T00:00:00Z",
                    "capture_kind": "rss_article",
                }
            ),
        }
    )
        self.assertEqual(item["headline"], "Example headline")
        self.assertEqual(item["canonical_url"], "https://publisher.example/news/article-001")
        self.assertEqual(item["publisher"], "Demo Publisher")
        self.assertEqual(item["capture_kind"], "rss_article")
        self.assertTrue(item["record_id"])

    def test_news_api_is_get_only_by_default(self) -> None:
        text = Path(api.__file__).read_text(encoding="utf-8")
        self.assertEqual(config.SCHEMA_VERSION, "news.v1")
        self.assertEqual(config.API_PORT, 8108)
        for path in ("/healthz", "/v1/metadata", "/v1/records", "/v1/history", "/v1/refresh"):
            self.assertIn(path, text)
        self.assertIn('data_status="forbidden"', text)
        self.assertFalse(config.ALLOW_REFRESH)

    @NEEDS_LAKE
    def test_history_deduplicates_replays_but_keeps_new_observation_times(self) -> None:
        base = {
            "source": "Matichon",
            "article_id": "article-001",
            "source_record_id": "Matichon|article-001",
            "canonical_url": "https://publisher.example/news/article-001",
            "headline": "Example headline",
            "event_time": "2026-09-08T00:00:00Z",
            "updated_at": "2026-09-08T00:00:00Z",
            "ingest_run_id": "run-001",
            "raw_object_key": "landing/batch-001/payload.csv",
        }
        duplicate = {**base, "ingest_run_id": "run-002", "raw_object_key": "landing/batch-002/payload.csv"}
        later = {**base, "event_time": "2026-09-08T01:00:00Z", "updated_at": "2026-09-08T01:00:00Z"}
        items = store.deduplicate_history_items([base, duplicate, later])
        self.assertEqual(len(items), 2)
        self.assertEqual([item["record_id"] for item in items], ["Matichon|article-001#h0", "Matichon|article-001#h1"])
