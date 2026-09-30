#!/usr/bin/env python3
"""Capture NotebookSpec articles from its public RSS feed.

This is a dedicated news adapter. Do not reuse ecommerce/Shopee modules for
this source. Durable news lake/API ownership belongs downstream.
"""

from __future__ import annotations

from functools import partial

from news import feed_adapter
from news.feed_adapter import MAX_ENTRIES, OUTPUT_DIR  # noqa: F401 - public constants

SPEC = feed_adapter.FeedSpec(
    key="notebookspec_tech",
    source_name="Notebookspec",
    label="NotebookSpec RSS feed",
    publisher="NotebookSpec",
    feed_url="https://notebookspec.com/web/feed",
    host_suffix="notebookspec.com",
    feed_paths=("/web/feed",),
    extras=feed_adapter.category_extras,
    extra_fields=("categories",),
    strip_feed_url_slash=True,
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


class NotebookspecScraper(feed_adapter.FeedScraper):
    """Scheduler adapter for bounded NotebookSpec RSS capture."""

    spec = SPEC


if __name__ == "__main__":
    import asyncio

    asyncio.run(NotebookspecScraper().run())
