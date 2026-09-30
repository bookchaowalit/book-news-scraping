#!/usr/bin/env python3
"""Capture Thai technology news from Blognone's public Atom-compatible feed."""

from __future__ import annotations

import re
from functools import partial
from typing import Any

from news import feed_adapter, feed_common
from news.feed_adapter import MAX_ENTRIES, OUTPUT_DIR  # noqa: F401 - public constants


def _article_id(entry: Any, url: str) -> str:
    match = re.search(r"/node/(\d+)(?:/|$)", url)
    if match:
        return match.group(1)
    return feed_common.clean_text(entry.get("id") or url, 300) or url


SPEC = feed_adapter.FeedSpec(
    key="thai_tech_news",
    source_name="Blognone",
    label="Blognone technology feed",
    publisher="Blognone",
    feed_url="https://www.blognone.com/atom.xml",
    host_suffix="blognone.com",
    feed_paths=("/atom.xml", "/node/feed"),
    exact_feed_urls=("https://www.blognone.com/atom.xml", "https://www.blognone.com/node/feed"),
    extras=feed_adapter.section_extras("technology", topics=True),
    extra_fields=("section", "topics"),
    feed_title_limit=240,
    article_id=_article_id,
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


class ThaiTechNewsScraper(feed_adapter.FeedScraper):
    """Scheduler adapter for bounded Blognone technology RSS capture."""

    spec = SPEC


if __name__ == "__main__":
    import asyncio

    asyncio.run(ThaiTechNewsScraper().run())
