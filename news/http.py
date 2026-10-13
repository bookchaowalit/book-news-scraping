"""Polite, bounded HTTP fetch shared by the RSS adapters.

Every adapter identifies itself with the same User-Agent, uses a finite
timeout, and retries only transient failures (timeouts, connection errors,
HTTP 429 and 5xx) with exponential backoff. Permanent client errors such as
403/404 fail immediately so a blocked feed is not hammered.
"""

from __future__ import annotations

import time
from typing import Callable

import httpx

USER_AGENT = "book-news-scraping/1.0 (+https://github.com/bookchaowalit/book-news-scraping)"
RSS_ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml"
DEFAULT_TIMEOUT = 30.0
DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF = 2.0
MAX_RETRY_AFTER = 60.0
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class FeedFetchError(RuntimeError):
    """Raised when a feed cannot be fetched after the bounded retries."""


def _retry_after_seconds(response: httpx.Response, fallback: float) -> float:
    raw = response.headers.get("Retry-After", "").strip()
    if raw.isdigit():
        return min(float(raw), MAX_RETRY_AFTER)
    return fallback


def fetch_bytes(
    url: str,
    *,
    source: str,
    accept: str = RSS_ACCEPT,
    timeout: float = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    backoff: float = DEFAULT_BACKOFF,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """Fetch ``url`` and return a non-empty body or raise ``FeedFetchError``."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    last_error = "unknown error"
    for attempt in range(1, attempts + 1):
        delay = backoff * (2 ** (attempt - 1))
        try:
            response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = type(exc).__name__
        else:
            status = getattr(response, "status_code", 200)
            if status in RETRYABLE_STATUS:
                last_error = f"HTTP {status}"
                delay = _retry_after_seconds(response, delay)
            else:
                response.raise_for_status()
                if not response.content:
                    raise ValueError(f"{source} response is empty")
                return response.content
        if attempt < attempts:
            sleep(delay)
    raise FeedFetchError(f"{source} fetch failed after {attempts} attempts: {last_error}")
