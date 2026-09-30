# Upgrade plan — book-news-scraping

## Current state

Score: **8/10** (pass 1: 5 -> 7; pass 2: 7 -> 7.5; pass 3: 7.5 -> 8) — four fixture-tested
RSS adapters on one shared helper module plus the `news.v1` read-only API,
polite fetching, per-feed failure isolation, lint, and offline CI. No legacy
code left; `updated_at` is now truthful.

## Backlog

### P0
- (none open)

### P1
- Confirm each opt-in feed (`bangkok_post_tech`, `thaiger_business`,
  `techcrunch_tech`) against the live site once (fixtures are synthetic,
  format-based), then register it in the parent `run_news_capture.NEWS_FEEDS`,
  ingest specs and coverage registry before adding it to the default roster.
- Techsauce (`https://techsauce.co/feed`): add as a `FeedSpec` only after its
  feed format is confirmed (not verifiable offline).

### P2
- Add a conditional GET (ETag/Last-Modified) cache to cut repeat traffic.
- Update PRODUCT.md "runtime collection remains scheduled by book-job-scraping"
  once the parent scheduler cut-over is confirmed.

## Done in this pass (pass 1)
- `news/http.py`: identifying UA, 30 s timeout, bounded retry with backoff on
  429/5xx/timeouts only, `Retry-After` capped at 60 s; all adapters use it.
- `scripts/run_feeds.py`: one failing feed no longer aborts the rest; errors
  are reported by exception class only; exit 1 if any feed failed.
- `news_data/store.py`: honours `SOLO_EMPIRE_ROOT` to find the parent lake
  helpers; the two lake tests skip cleanly when they are absent (previously
  failed in a standalone checkout).
- Added `ruff.toml`, `pytest.ini`, GitHub Actions CI; fixed lint errors;
  untracked committed `__pycache__`.

## Done in this pass (pass 2)
- New `news/feed_common.py` (text cleaning, timestamp parsing with a source
  timezone, image/tag extraction, CSV/raw writers); the four adapters use it
  (~350 duplicated lines removed).
- `updated_at` no longer silently copies `published_at`: the feedparser
  fallback is bypassed and pytest errors on its DeprecationWarning.
- Removed `news/thai_news_scraper.py` (retired monorepo imports); remaining
  feeds it covered are in the P1 backlog.
- `tests/test_feed_common.py`: helper tests plus empty/garbage/off-site feed
  error paths for every adapter (21 -> 28 tests, +16 subtests).

## Done in this pass (pass 3)
- New `news/feed_adapter.py`: `FeedSpec` (host suffix, accepted feed paths or
  exact URLs, source timezone, row extras + columns, article-id rule, file
  stem, labels) with one generic `parse_feed`/URL policy/writers and a
  `FeedScraper` base. The four adapters are now ~50-line specs that keep
  their public module API; parsed rows, snapshot columns and feed-URL policy
  verified byte-identical against the previous code on all four fixtures.
- New config-only opt-in feeds in `news/optional_feeds.py`: Bangkok Post Tech,
  Thaiger Business, TechCrunch (URLs from the retired legacy roster), with
  synthetic RSS 2.0 / WordPress-shaped fixtures. Kept out of the default
  roster because the parent News contract registers only four sources;
  `scripts/run_feeds.py --feeds NAME...` selects them (unknown names exit 2).
  Techsauce left out (format unconfirmed).
- `tests/test_optional_feeds.py` (8 tests): timezone, dedup, off-site /
  plain-HTTP / lookalike-host drops, WordPress author/topics/guid, feed-URL
  policy, writers, roster selection. 28 -> 36 passed; ruff 0.15.8 and
  0.16.9 clean.
- Refresh auth: `/v1/refresh` compares the bearer token with `hmac.compare_digest`
  (`_refresh_token_ok`) instead of `==`, which leaked the matching prefix
  length through timing; `tests/test_refresh_token_compare.py` pins it.
- Text edge cases in `feed_common.clean_text`: plain titles with a bare
  "<" ("Why x<y matters") were cut to "Why x" by the HTML parser; markup is
  now parsed only when real tags are present. Entities inside markup were
  decoded twice ("&amp;lt;div&amp;gt;" became a literal "<div>"); now once.
  Zero-width space / word joiner / BOM are removed, and the length limit no
  longer splits a grapheme (Thai tone marks and sara am, emoji modifiers and
  ZWJ sequences) via `truncate_text`. 4 regression tests.
