# Upgrade plan — book-news-scraping

## Current state

Score: **7/10** (was 5/10) — four fixture-tested RSS adapters plus the
`news.v1` read-only API; now with shared polite fetching, per-feed failure
isolation, lint, and offline CI. Remaining gaps are the legacy module and
duplicated adapter code.

## Backlog

### P0
- (none open)

### P1
- Collapse the four near-identical adapters (`canonical_url`, `_clean_text`,
  `_published_at`, CSV writers) into one shared module with per-feed config;
  keep the fixture tests as the regression net.
- Resolve the feedparser `updated`→`published` DeprecationWarning: read
  `entry.get("updated_parsed")`/raw `updated` explicitly so `updated_at` does
  not silently fall back to `published_at`.
- Delete or port `news/thai_news_scraper.py` (depends on missing monorepo
  `adapters`/`core` packages).

### P2
- Add a fixture test for a malformed/empty feed per adapter (error paths).
- Add a conditional GET (ETag/Last-Modified) cache to cut repeat traffic.
- Update PRODUCT.md "runtime collection remains scheduled by book-job-scraping"
  once the parent scheduler cut-over is confirmed.

## Done in this pass
- `news/http.py`: identifying UA, 30 s timeout, bounded retry with backoff on
  429/5xx/timeouts only, `Retry-After` capped at 60 s; all adapters use it.
- `scripts/run_feeds.py`: one failing feed no longer aborts the rest; errors
  are reported by exception class only; exit 1 if any feed failed.
- `news_data/store.py`: honours `SOLO_EMPIRE_ROOT` to find the parent lake
  helpers; the two lake tests skip cleanly when they are absent (previously
  failed in a standalone checkout).
- Added `ruff.toml`, `pytest.ini`, GitHub Actions CI; fixed lint errors;
  untracked committed `__pycache__`.
