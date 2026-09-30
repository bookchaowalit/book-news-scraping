#!/usr/bin/env python3
"""Run the bounded RSS adapters owned by this repository.

book-job-scraping may still schedule the same sources as a compatibility
collector. This runner writes only under this repository's data/ directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news.matichon_scraper import MatichonScraper
from news.notebookspec_scraper import NotebookspecScraper
from news.thai_business_scraper import ThaiBusinessNewsScraper
from news.thai_tech_scraper import ThaiTechNewsScraper

FEEDS = (
    ("matichon_news", MatichonScraper),
    ("thai_business_news", ThaiBusinessNewsScraper),
    ("thai_tech_news", ThaiTechNewsScraper),
    ("notebookspec_tech", NotebookspecScraper),
)


async def run_feeds(output_dir: Path, limit: int = 50, feeds=FEEDS) -> list[dict[str, Any]]:
    """Run every feed; one failing publisher must not block the others.

    Failures are reported as ``{"source": name, "error": <class>}`` entries.
    Only the exception class is recorded so publisher payloads never leak
    into logs.
    """

    results: list[dict[str, Any]] = []
    for name, cls in feeds:
        try:
            scraper = cls(limit=limit, output_dir=output_dir)
            batch = await scraper.run()
        except Exception as exc:  # noqa: BLE001 - isolate each publisher
            results.append({"source": name, "error": type(exc).__name__})
            print(f"[run_feeds] {name}: failed ({type(exc).__name__})", file=sys.stderr)
            continue
        results.extend(batch)
        print(f"[run_feeds] {name}: {batch[0].get('count') if batch else 0}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run book-news-scraping RSS feeds")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "exported")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = asyncio.run(run_feeds(args.output_dir, args.limit))
    if args.json:
        print(json.dumps(results, ensure_ascii=False))
    # Non-zero when any feed failed so the parent control plane still treats
    # the cycle as incomplete.
    return 1 if any("error" in result for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
