"""Shared helpers for the feed-specific RSS/Atom adapters.

Each adapter keeps its own source policy (allowed host, feed URL, output file
names, row shape); the text cleaning, date parsing and CSV writing that used
to be copied into every adapter live here.
"""

from __future__ import annotations

import csv
import html as html_lib
import re
from datetime import datetime, timezone, tzinfo
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from bs4 import BeautifulSoup


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: Any, limit: int) -> str:
    """Unescape entities, strip markup and collapse whitespace."""

    text = html_lib.unescape(str(value or ""))
    if "<" in text or ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _raw(entry: Any, key: str) -> Any:
    """Read ``key`` without feedparser's ``updated`` -> ``published`` fallback.

    ``FeedParserDict`` maps a missing ``updated`` to ``published`` with a
    DeprecationWarning; that silently made ``updated_at`` equal
    ``published_at``. ``in`` checks the real key only.
    """

    if key in ("updated", "updated_parsed"):
        return entry[key] if key in entry else None
    return entry.get(key)


def parse_timestamp(value: Any, default_tz: tzinfo = timezone.utc) -> str:
    """Return an ISO-8601 UTC ``...Z`` string, or ``""`` when unparseable."""

    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_tz)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def published_at(entry: Any, default_tz: tzinfo = timezone.utc) -> str:
    """First parseable of ``published``/``updated``/``created``."""

    for key in ("published", "updated", "created"):
        value = parse_timestamp(_raw(entry, key), default_tz)
        if value:
            return value
    return ""


def updated_at(entry: Any, default_tz: tzinfo = timezone.utc) -> str:
    """The entry's own ``updated`` time only; ``""`` when the feed has none."""

    return parse_timestamp(_raw(entry, "updated"), default_tz)


def image_url(entry: Any) -> str:
    for key in ("media_content", "media_thumbnail", "enclosures"):
        values = entry.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict) and value.get("url"):
                return str(value["url"]).strip()
    return ""


def tag_terms(entry: Any, limit: int = 10) -> str:
    """Comma-joined, de-duplicated tag terms (at most ``limit``)."""

    values = entry.get("tags")
    if not isinstance(values, list):
        return ""
    terms: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        term = clean_text(value.get("term"), 80)
        if term and term not in terms:
            terms.append(term)
    return ",".join(terms[:limit])


def write_bytes(raw: bytes, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def write_snapshot(
    path: Path, fields: list[str], rows: Iterable[Mapping[str, Any]], captured_at: str
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "captured_at": captured_at})
    return path


def append_history(
    path: Path, fields: list[str], rows: Iterable[Mapping[str, Any]], captured_at: str
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({**row, "captured_at": captured_at})
    return path
