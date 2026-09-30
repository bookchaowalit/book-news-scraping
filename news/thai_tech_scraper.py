#!/usr/bin/env python3
"""Capture Thai technology news from Blognone's public Atom-compatible feed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    import feedparser
except ImportError as exc:  # pragma: no cover - requirements.txt supplies dependencies
    raise RuntimeError("feedparser, httpx, and beautifulsoup4 are required for Blognone capture") from exc

from news import feed_common
from news.http import fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "exported"
FEED_URL = "https://www.blognone.com/atom.xml"
SOURCE_NAME = "Blognone"
MAX_ENTRIES = 100
ALLOWED_HOST = re.compile(r"(?:[a-z0-9-]+\.)*blognone\.com", re.IGNORECASE)
SNAPSHOT_FIELDS = [
    "captured_at",
    "article_id",
    "title",
    "url",
    "summary",
    "author",
    "section",
    "topics",
    "published_at",
    "updated_at",
    "image_url",
    "source",
    "source_url",
    "feed_title",
]
HISTORY_FIELDS = ["captured_at", "article_id", "title", "url", "published_at", "source"]


def canonical_url(value: str) -> str:
    parts = urlsplit(str(value).strip())
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() != "https" or not ALLOWED_HOST.fullmatch(host):
        raise ValueError("Blognone article URL must use an HTTPS blognone.com host")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, "", ""))


def normalize_feed_url(value: str) -> str:
    url = canonical_url(value)
    if url.rstrip("/") not in {"https://www.blognone.com/atom.xml", "https://www.blognone.com/node/feed"}:
        raise ValueError("Blognone feed URL must be /atom.xml or /node/feed")
    return url


def _article_id(entry: Any, url: str) -> str:
    match = re.search(r"/node/(\d+)(?:/|$)", url)
    if match:
        return match.group(1)
    return feed_common.clean_text(entry.get("id") or url, 300) or url


def parse_feed(raw: bytes | str, feed_url: str = FEED_URL, limit: int = 50) -> tuple[Any, list[dict[str, Any]]]:
    normalized_feed_url = normalize_feed_url(feed_url)
    parsed = feedparser.parse(raw)
    if not parsed.entries:
        raise ValueError("Blognone technology feed contains no entries")
    feed_title = feed_common.clean_text(parsed.feed.get("title"), 240)
    if not feed_title:
        raise ValueError("Blognone technology feed title is missing")

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
        rows.append(
            {
                "article_id": _article_id(entry, url),
                "title": title,
                "url": url,
                "summary": feed_common.clean_text(entry.get("summary") or entry.get("description"), 1000),
                "author": feed_common.clean_text(entry.get("author") or entry.get("dc_creator"), 160),
                "section": "technology",
                "topics": feed_common.tag_terms(entry),
                "published_at": published_at,
                "updated_at": feed_common.updated_at(entry),
                "image_url": feed_common.image_url(entry),
                "source": SOURCE_NAME,
                "source_url": normalized_feed_url,
                "feed_title": feed_title,
            }
        )
        seen_urls.add(url)
        if len(rows) >= limit:
            break
    if not rows:
        raise ValueError("Blognone technology feed contains no contract-compliant entries")
    return parsed, rows


def fetch_feed(feed_url: str) -> bytes:
    return fetch_bytes(normalize_feed_url(feed_url), source="Blognone technology feed")


def write_raw(raw: bytes, output_dir: Path) -> Path:
    return feed_common.write_bytes(raw, output_dir / "thai_tech_news_raw.xml")


def write_snapshot(rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.write_snapshot(output_dir / "thai_tech_news.csv", SNAPSHOT_FIELDS, rows, captured_at)


def append_history(rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.append_history(output_dir / "thai_tech_news_history.csv", HISTORY_FIELDS, rows, captured_at)


class ThaiTechNewsScraper:
    """Scheduler adapter for bounded Blognone technology RSS capture."""

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
        print(f"[thai_tech_news] {len(rows)} articles -> {snapshot_path}")
        return [
            {
                "source": "thai_tech_news",
                "count": len(rows),
                "output": str(snapshot_path),
                "history": str(history_path),
                "raw": str(raw_path),
            }
        ]


if __name__ == "__main__":
    import asyncio

    asyncio.run(ThaiTechNewsScraper().run())
