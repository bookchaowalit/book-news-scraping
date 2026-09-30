#!/usr/bin/env python3
"""Capture Matichon Online articles from its public RSS feed.

The RSS feed is the preferred acquisition channel for this source. This repo
only produces a bounded, validated capture; durable news lake/API ownership
belongs to the downstream data product.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    import feedparser
except ImportError as exc:  # pragma: no cover - requirements.txt supplies dependencies
    raise RuntimeError("feedparser, httpx, and beautifulsoup4 are required for Matichon capture") from exc

from news import feed_common
from news.http import fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "exported"
FEED_URL = "https://www.matichon.co.th/feed"
MAX_ENTRIES = 100
ALLOWED_HOST = re.compile(r"(?:[a-z0-9-]+\.)*matichon\.co\.th", re.IGNORECASE)
SNAPSHOT_FIELDS = [
    "captured_at",
    "article_id",
    "title",
    "url",
    "summary",
    "author",
    "categories",
    "published_at",
    "updated_at",
    "image_url",
    "source",
    "source_url",
    "feed_title",
]
HISTORY_FIELDS = ["captured_at", "article_id", "title", "url", "published_at", "source"]


def canonical_url(value: str) -> str:
    """Normalize and keep only HTTPS Matichon article URLs."""

    parts = urlsplit(str(value).strip())
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() != "https" or not ALLOWED_HOST.fullmatch(host):
        raise ValueError("Matichon article URL must use an HTTPS matichon.co.th host")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, "", ""))


def normalize_feed_url(value: str) -> str:
    url = canonical_url(value)
    if not url.rstrip("/").endswith("/feed"):
        raise ValueError("Matichon feed URL must end with /feed")
    return url


def parse_feed(raw: bytes | str, feed_url: str = FEED_URL, limit: int = 50) -> tuple[Any, list[dict[str, Any]]]:
    """Parse RSS entries, dropping entries without trustworthy attribution."""

    normalized_feed_url = normalize_feed_url(feed_url)
    parsed = feedparser.parse(raw)
    if not parsed.entries:
        raise ValueError("Matichon RSS feed contains no entries")
    feed_title = feed_common.clean_text(parsed.feed.get("title"), 200)
    if not feed_title:
        raise ValueError("Matichon RSS feed title is missing")

    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for entry in parsed.entries[:limit]:
        title = feed_common.clean_text(entry.get("title"), 300)
        link = str(entry.get("link") or entry.get("id") or "").strip()
        if not title or not link:
            continue
        try:
            url = canonical_url(link)
        except ValueError:
            continue
        if url in seen_urls:
            continue
        published_at = feed_common.published_at(entry)
        if not published_at:
            continue
        article_id = feed_common.clean_text(entry.get("id") or url, 300)
        if not article_id:
            article_id = url
        rows.append(
            {
                "article_id": article_id,
                "title": title,
                "url": url,
                "summary": feed_common.clean_text(entry.get("summary") or entry.get("description"), 1000),
                "author": feed_common.clean_text(entry.get("author") or entry.get("dc_creator"), 160),
                "categories": feed_common.tag_terms(entry),
                "published_at": published_at,
                "updated_at": feed_common.updated_at(entry),
                "image_url": feed_common.image_url(entry),
                "source": "Matichon",
                "source_url": normalized_feed_url,
                "feed_title": feed_title,
            }
        )
        seen_urls.add(url)
        if len(rows) >= limit:
            break
    if not rows:
        raise ValueError("Matichon RSS feed contains no contract-compliant entries")
    return parsed, rows


def fetch_feed(feed_url: str) -> bytes:
    return fetch_bytes(normalize_feed_url(feed_url), source="Matichon RSS")


def write_raw(raw: bytes, output_dir: Path) -> Path:
    return feed_common.write_bytes(raw, output_dir / "matichon_news_raw.xml")


def write_snapshot(rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.write_snapshot(output_dir / "matichon_news.csv", SNAPSHOT_FIELDS, rows, captured_at)


def append_history(rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.append_history(output_dir / "matichon_news_history.csv", HISTORY_FIELDS, rows, captured_at)


class MatichonScraper:
    """Scheduler adapter for bounded Matichon RSS capture."""

    def __init__(
        self,
        feed_url: str = FEED_URL,
        limit: int = 50,
        output_dir: str | Path | None = None,
        **_: Any,
    ) -> None:
        self.feed_url = normalize_feed_url(feed_url)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ENTRIES:
            raise ValueError(f"limit must be an integer from 1 to {MAX_ENTRIES}")
        self.limit = limit
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR

    async def run(self, **_: Any) -> list[dict[str, Any]]:
        raw = fetch_feed(self.feed_url)
        _, rows = parse_feed(raw, self.feed_url, self.limit)
        captured_at = feed_common.utc_now()
        raw_path = write_raw(raw, self.output_dir)
        snapshot_path = write_snapshot(rows, captured_at, self.output_dir)
        history_path = append_history(rows, captured_at, self.output_dir)
        print(f"[matichon_news] {len(rows)} articles -> {snapshot_path}")
        return [
            {
                "source": "matichon_news",
                "count": len(rows),
                "output": str(snapshot_path),
                "history": str(history_path),
                "raw": str(raw_path),
            }
        ]


if __name__ == "__main__":
    import asyncio

    asyncio.run(MatichonScraper().run())
