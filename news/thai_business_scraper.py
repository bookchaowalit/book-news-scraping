#!/usr/bin/env python3
"""Capture Bangkok Post Business articles from its public RSS feed.

This is a feed-specific adapter for the shared acquisition layer. It preserves
the source section and feed attribution while writing only local capture
artifacts for downstream news-lake ingestion.
"""

from __future__ import annotations

from functools import partial
from zoneinfo import ZoneInfo

from news import feed_adapter
from news.feed_adapter import MAX_ENTRIES, OUTPUT_DIR  # noqa: F401 - public constants

SPEC = feed_adapter.FeedSpec(
    key="thai_business_news",
    source_name="Bangkok Post Business",
    label="Bangkok Post Business RSS feed",
    publisher="Bangkok Post",
    feed_url="https://www.bangkokpost.com/rss/data/business.xml",
    host_suffix="bangkokpost.com",
    feed_paths=("/rss/data/business.xml",),
    extras=feed_adapter.section_extras("business"),
    extra_fields=("section",),
    # Bangkok Post pubDates can be naive; they are Bangkok local time.
    source_timezone=ZoneInfo("Asia/Bangkok"),
)
FEED_URL = SPEC.feed_url
SOURCE_NAME = SPEC.source_name
ALLOWED_HOST = SPEC.allowed_host
SNAPSHOT_FIELDS = SPEC.snapshot_fields
HISTORY_FIELDS = SPEC.history_fields

canonical_url = partial(feed_adapter.canonical_url, SPEC)
normalize_feed_url = partial(feed_adapter.normalize_feed_url, SPEC)
parse_feed = partial(feed_adapter.parse_feed, SPEC)
fetch_feed = partial(feed_adapter.fetch_feed, SPEC)
write_raw = partial(feed_adapter.write_raw, SPEC)
write_snapshot = partial(feed_adapter.write_snapshot, SPEC)
append_history = partial(feed_adapter.append_history, SPEC)


class ThaiBusinessNewsScraper(feed_adapter.FeedScraper):
    """Scheduler adapter for bounded Bangkok Post Business RSS capture."""

    spec = SPEC


if __name__ == "__main__":
    import asyncio

    asyncio.run(ThaiBusinessNewsScraper().run())
