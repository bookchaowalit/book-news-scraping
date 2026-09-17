# book-news-scraping

**Tier:** C / tool prototype (portfolio breadth, not interview flagship)  
**Owner path:** `bookchaowalit/book-apps/tools/book-news-scraping`

## Purpose

Thai news headline/article fetch prototypes (Matichon and generic Thai news modules).

## Entry points

- `news/matichon_scraper.py, news/thai_news_scraper.py`

## Stack

Python

## How to run (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_feeds.py --limit 20
bash setup_cron.sh plan      # read-only; prints the parent lake runner entry
bash setup_cron.sh status
```

Adapters: Matichon, Bangkok Post Business, Blognone, NotebookSpec.
Output stays in this repository's `data/exported/`. The book-job-scraping
scheduler may still collect the same feeds as a compatibility runner.

The approved captures can be replayed into the shared Bronze lake with the
parent operator command:

```bash
task scraping:ingest -- --product news
task scraping:stack -- --require-job-readiness
```

For one bounded collection-to-lake cycle, run the parent control-plane command
with an explicit writable lake path:

```bash
task scraping:news:run -- \
  --lake-uri /absolute/path/to/data/lake \
  --attempts 2 --collector-timeout-seconds 120 --json
```

The command acquires the News source lock, runs the RSS collector, validates
all eight snapshot/history captures before replay, and writes Bronze
idempotently. Cumulative history CSVs are committed as append deltas while the
full capture bytes remain in immutable landing, and the API removes exact
replay duplicates as a defense-in-depth measure. Health checks require every
feed to have a fresh current record and require the read path to stay on
Parquet. If ingest or health fails, bounded retries replay the same validated
capture without hitting RSS again. It does not install cron or enable the API
refresh endpoint.

The read-only `news.v1` API listens on `127.0.0.1:8108` and serves committed
Bronze data only. Consumers must use `GET /v1/records` (or `/v1/history`) and
preserve publisher attribution; they must not read these CSVs directly.

The scheduler plan uses the same control-plane runner and source lock. Review
it with an explicit lake before any installation:

```bash
SOLO_EMPIRE_DATA_LAKE_URI=/absolute/path/to/shared/lake bash setup_cron.sh plan
```

Installation requires `SOLO_EMPIRE_DATA_LAKE_URI` and refuses a missing or
non-writable local path. When approved, `bash setup_cron.sh install` runs the
bounded runner every two hours at minute 15, writes JSON logs, and keeps the
collector lock shared with the domain boundary. It uses the parent
`infra/scripts/setup/run-python3.sh` runtime and checks for `duckdb`,
`feedparser`, and `pyarrow` before installing. The plan command never edits
crontab.

## Boundaries

- **Lake/API boundary:** capture remains owned here; the parent operator owns
  replay orchestration and the shared lake runtime, while this repository owns
  the `news.v1` read-only delivery adapter.
- **Not** coupled to upstream consumer apps. Nested Git repo; commit only inside this tree.
- Never commit `.env`, cookies, session dumps, or scraped PII dumps to Git.

## Limitations (honest)

Publishers may disallow automated access. Only publisher-provided RSS/Atom
captures with canonical URLs and attribution are approved. The API does not
republish article bodies or trigger collection from a read request.

## Related

- Active collection product: `book-job-scraping` (Tier A tool)
- Lake products: `book-crypto-data`, `book-fx-data`, `book-stock-data`, …
- Solo Empire catalog: `repository-catalog/BOOK-DEV-BACKLOG-BD.md` (BD-012)
