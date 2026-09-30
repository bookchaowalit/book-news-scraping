#!/usr/bin/env python3
"""Capture Matichon Online articles from its public RSS feed.

The RSS feed is the preferred acquisition channel for this source. This repo
only produces a bounded, validated capture; durable news lake/API ownership
belongs to the downstream data product.
"""

from __future__ import annotations

from functools import partial

from news import feed_adapter
from news.feed_adapter import MAX_ENTRIES, OUTPUT_DIR  # noqa: F401 - public constants

SPEC = feed_adapter.FeedSpec(
    key="matichon_news",
    source_name="Matichon",
    label="Matichon RSS feed",
    publisher="Matichon",
    feed_url="https://www.matichon.co.th/feed",
    host_suffix="matichon.co.th",
    feed_paths=("/feed",),
    extras=feed_adapter.category_extras,
    extra_fields=("categories",),
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


class MatichonScraper(feed_adapter.FeedScraper):
    """Scheduler adapter for bounded Matichon RSS capture."""

    spec = SPEC


if __name__ == "__main__":
    import asyncio

    asyncio.run(MatichonScraper().run())
