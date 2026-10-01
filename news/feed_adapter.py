"""One generic RSS/Atom adapter driven by a per-feed ``FeedSpec``.

Every feed module used to carry its own copy of URL policy, parsing, writers
and the scheduler class. The policy that actually differs per publisher (host,
accepted feed URLs, timezone, row extras, file stem, labels) now lives in a
``FeedSpec``; parsing and capture are shared, so a new feed is config-only
plus a fixture test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timezone, tzinfo
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

try:
    import feedparser
except ImportError as exc:  # pragma: no cover - requirements.txt supplies dependencies
    raise RuntimeError("feedparser, httpx, and beautifulsoup4 are required for RSS capture") from exc

from news import feed_common
from news.http import fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "exported"
MAX_ENTRIES = 100
HISTORY_FIELDS = ["captured_at", "article_id", "title", "url", "published_at", "source"]
_BASE_SNAPSHOT_FIELDS = ["captured_at", "article_id", "title", "url", "summary", "author"]
_TAIL_SNAPSHOT_FIELDS = ["published_at", "updated_at", "image_url", "source", "source_url", "feed_title"]

Extras = Callable[[Any], dict[str, str]]
ArticleId = Callable[[Any, str], str]


def entry_id(entry: Any, url: str) -> str:
    """Default article id: the feed's ``id``/``guid``, else the canonical URL."""

    return feed_common.clean_text(entry.get("id") or url, 300) or url


def section_extras(section: str, *, topics: bool = False) -> Extras:
    """Row extras for feeds that report a fixed section (optionally plus tag topics)."""

    def extras(entry: Any) -> dict[str, str]:
        row = {"section": section}
        if topics:
            row["topics"] = feed_common.tag_terms(entry)
        return row

    return extras


def category_extras(entry: Any) -> dict[str, str]:
    """Row extras for feeds whose ``<category>`` tags are the classification."""

    return {"categories": feed_common.tag_terms(entry)}


@dataclass(frozen=True)
class FeedSpec:
    """Publisher policy for one feed. Only this differs between adapters."""

    key: str  # scheduler source name and output file stem
    source_name: str  # ``source`` column value (the News contract label)
    label: str  # human label used in error messages, e.g. "Matichon RSS feed"
    publisher: str  # short publisher name used in URL errors
    feed_url: str
    host_suffix: str  # registrable domain, e.g. "bangkokpost.com"
    feed_paths: tuple[str, ...]  # accepted feed URL path suffixes
    extras: Extras
    extra_fields: tuple[str, ...]  # snapshot columns produced by ``extras``
    exact_feed_urls: tuple[str, ...] = ()  # when set, only these full URLs are accepted
    source_timezone: tzinfo = timezone.utc
    feed_title_limit: int = 200
    article_id: ArticleId = entry_id
    strip_feed_url_slash: bool = False
    allowed_host: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        pattern = r"(?:[a-z0-9-]+\.)*" + re.escape(self.host_suffix)
        object.__setattr__(self, "allowed_host", re.compile(pattern, re.IGNORECASE))

    @property
    def snapshot_fields(self) -> list[str]:
        return [*_BASE_SNAPSHOT_FIELDS, *self.extra_fields, *_TAIL_SNAPSHOT_FIELDS]

    @property
    def history_fields(self) -> list[str]:
        return list(HISTORY_FIELDS)


def canonical_url(spec: FeedSpec, value: str) -> str:
    """HTTPS URL on the publisher's host, without query, fragment or trailing slash."""

    parts = urlsplit(str(value).strip())
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() != "https" or not spec.allowed_host.fullmatch(host):
        raise ValueError(f"{spec.publisher} article URL must use an HTTPS {spec.host_suffix} host")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, "", ""))


def normalize_feed_url(spec: FeedSpec, value: str) -> str:
    url = canonical_url(spec, value)
    trimmed = url.rstrip("/")
    if spec.exact_feed_urls:
        accepted = trimmed in {candidate.rstrip("/") for candidate in spec.exact_feed_urls}
    else:
        accepted = any(trimmed.endswith(path.rstrip("/")) for path in spec.feed_paths)
    if not accepted:
        raise ValueError(f"{spec.publisher} feed URL must end with {' or '.join(spec.feed_paths)}")
    return trimmed if spec.strip_feed_url_slash else url


def parse_feed(
    spec: FeedSpec, raw: bytes | str, feed_url: str | None = None, limit: int = 50
) -> tuple[Any, list[dict[str, Any]]]:
    """Parse entries, dropping any without an on-site HTTPS link, title or date."""

    normalized_feed_url = normalize_feed_url(spec, feed_url or spec.feed_url)
    parsed = feedparser.parse(raw)
    if not parsed.entries:
        raise ValueError(f"{spec.label} contains no entries")
    feed_title = feed_common.clean_text(parsed.feed.get("title"), spec.feed_title_limit)
    if not feed_title:
        raise ValueError(f"{spec.label} title is missing")

    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for entry in parsed.entries[:limit]:
        title = feed_common.clean_text(entry.get("title"), 300)
        link = str(entry.get("link") or entry.get("id") or "").strip()
        if not title or not link:
            continue
        try:
            url = canonical_url(spec, link)
        except ValueError:
            continue
        if url in seen_urls:
            continue
        published_at = feed_common.published_at(entry, spec.source_timezone)
        if not published_at:
            continue
        rows.append(
            {
                "article_id": spec.article_id(entry, url),
                "title": title,
                "url": url,
                "summary": feed_common.clean_text(entry.get("summary") or entry.get("description"), 1000),
                "author": feed_common.clean_text(entry.get("author") or entry.get("dc_creator"), 160),
                **spec.extras(entry),
                "published_at": published_at,
                "updated_at": feed_common.updated_at(entry, spec.source_timezone),
                "image_url": feed_common.image_url(entry),
                "source": spec.source_name,
                "source_url": normalized_feed_url,
                "feed_title": feed_title,
            }
        )
        seen_urls.add(url)
        if len(rows) >= limit:
            break
    if not rows:
        raise ValueError(f"{spec.label} contains no contract-compliant entries")
    return parsed, rows


def fetch_feed(spec: FeedSpec, feed_url: str) -> bytes:
    return fetch_bytes(normalize_feed_url(spec, feed_url), source=spec.label)


def write_raw(spec: FeedSpec, raw: bytes, output_dir: Path) -> Path:
    return feed_common.write_bytes(raw, output_dir / f"{spec.key}_raw.xml")


def write_snapshot(spec: FeedSpec, rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.write_snapshot(output_dir / f"{spec.key}.csv", spec.snapshot_fields, rows, captured_at)


def append_history(spec: FeedSpec, rows: list[dict[str, Any]], captured_at: str, output_dir: Path) -> Path:
    return feed_common.append_history(output_dir / f"{spec.key}_history.csv", spec.history_fields, rows, captured_at)


class FeedScraper:
    """Scheduler adapter for one bounded feed capture; subclasses set ``spec``."""

    spec: FeedSpec

    def __init__(
        self,
        feed_url: str | None = None,
        limit: int = 50,
        output_dir: str | Path | None = None,
        **_: Any,
    ) -> None:
        self.feed_url = normalize_feed_url(self.spec, feed_url or self.spec.feed_url)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ENTRIES:
            raise ValueError(f"limit must be an integer from 1 to {MAX_ENTRIES}")
        self.limit = limit
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR

    async def run(self, **_: Any) -> list[dict[str, Any]]:
        spec = self.spec
        raw = fetch_feed(spec, self.feed_url)
        _, rows = parse_feed(spec, raw, self.feed_url, self.limit)
        captured_at = feed_common.utc_now()
        raw_path = write_raw(spec, raw, self.output_dir)
        snapshot_path = write_snapshot(spec, rows, captured_at, self.output_dir)
        history_path = append_history(spec, rows, captured_at, self.output_dir)
        print(f"[{spec.key}] {len(rows)} articles -> {snapshot_path}")
        return [
            {
                "source": spec.key,
                "count": len(rows),
                "output": str(snapshot_path),
                "history": str(history_path),
                "raw": str(raw_path),
            }
        ]



def scraper_class(spec: FeedSpec, name: str, module: str) -> type[FeedScraper]:
    """Build a named ``FeedScraper`` subclass for a config-only feed."""

    doc = f"Scheduler adapter for bounded {spec.label} capture."
    return type(name, (FeedScraper,), {"spec": spec, "__doc__": doc, "__module__": module})
