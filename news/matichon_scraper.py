#!/usr/bin/env python3
"""
Matichon RSS scraper — Thai news from matichon.co.th.

Data: 50 news articles per run with title, link, description, pubDate, category
"""

import asyncio
import csv
import json
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from adapters.outbound.engines.base import BaseScraper

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"

RSS_URL = "https://www.matichon.co.th/feed"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml",
}


class MatichonScraper(BaseScraper):
    """Scrape Thai news from Matichon RSS feed."""

    def __init__(self, **kwargs):
        super().__init__(
            name="matichon",
            rate_limit=kwargs.get("rate_limit", 2.0),
            max_retries=3,
            timeout=30.0,
        )

    async def fetch_feed(self) -> Optional[str]:
        """Fetch the RSS feed."""
        await self._wait_for_rate_limit()
        self.stats["requests"] += 1

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    resp = await client.get(RSS_URL, headers=HEADERS)
                    if resp.status_code >= 400:
                        logger.warning(f"[HTTP {resp.status_code}] {RSS_URL}")
                        continue
                    self.stats["misses"] += 1
                    return resp.text
            except Exception as e:
                logger.error(f"[ERROR] {RSS_URL}: {e} (attempt {attempt+1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        self.stats["errors"] += 1
        return None

    def parse_feed(self, xml_content: str) -> List[dict]:
        """Parse RSS XML and extract articles."""
        if not xml_content:
            return []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []

        items = []
        channel = root.find("channel")
        if channel is None:
            return []

        # Handle namespaces
        ns = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "content": "http://purl.org/rss/1.0/modules/content/",
        }

        for item in channel.findall("item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            category = item.findtext("category", "").strip()
            creator = item.findtext("dc:creator", "", ns).strip()

            # Strip HTML tags from description
            import re
            description = re.sub(r"<[^>]+>", "", description).strip()
            if len(description) > 300:
                description = description[:300] + "..."

            if not title:
                continue

            items.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date,
                "category": category,
                "author": creator,
                "source": "matichon",
                "language": "th",
            })

        return items

    async def run(self, **kwargs):
        """Run the scraper."""
        logger.info("Scraping Matichon RSS feed...")

        xml_content = await self.fetch_feed()
        if not xml_content:
            logger.error("Failed to fetch RSS feed")
            return []

        items = self.parse_feed(xml_content)
        for item in items:
            self.add_result(item)

        logger.info(f"Found {len(items)} articles")

        self.print_stats()
        self.export_csv("matichon_articles.csv")
        self.export_json("matichon_articles.json")

        if self.results:
            save_results(self.results, OUTPUT_DIR)

        return self.results


def save_results(results: list, output_dir: Path):
    """Save results to data/ directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "title", "link", "description", "pub_date",
        "category", "author", "source", "language", "scraped_at",
    ]

    csv_path = output_dir / "matichon_articles.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    history_path = output_dir / "matichon_history.csv"
    file_exists = history_path.exists()
    with open(history_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        now = datetime.now().isoformat()
        for r in results:
            row = {**r, "scraped_at": now}
            writer.writerow(row)

    logger.info(f"Saved {len(results)} articles to {csv_path}")


async def main():
    scraper = MatichonScraper()
    results = await scraper.run()
    print(f"\nTotal articles scraped: {len(results)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
