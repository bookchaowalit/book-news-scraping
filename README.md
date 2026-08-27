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
bash setup_cron.sh install   # optional; every 2 hours
bash setup_cron.sh status
```

Adapters: Matichon, Bangkok Post Business, Blognone, NotebookSpec.
Output stays in this repository's `data/exported/`. The book-job-scraping
scheduler may still collect the same feeds as a compatibility runner.

## Boundaries

- **Not** a lake-first data product. Durable market datasets live under `book-*-data` repos.
- **Not** coupled to Solo Empire monorepo runtime. Nested Git repo; commit only inside this tree.
- Never commit `.env`, cookies, session dumps, or scraped PII dumps to Git.

## Limitations (honest)

Publishers may disallow automated access. No republishing pipeline. Not connected to a lake product yet.

## Related

- Active collection product: `book-job-scraping` (Tier A tool)
- Lake products: `book-crypto-data`, `book-fx-data`, `book-stock-data`, …
- Solo Empire catalog: `repository-catalog/BOOK-DEV-BACKLOG-BD.md` (BD-012)
