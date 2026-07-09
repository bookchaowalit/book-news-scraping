#!/usr/bin/env python3
"""
Thai News RSS scraper — uses RSS engine.
Scrapes business and tech news from Bangkok Post, Techsauce, Thaiger, TechCrunch.

MCP Tool: get_news
Data: title, link, summary, published date, author, tags
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.outbound.engines.rss_engine import RSSScraper
from core.models import NewsArticle

logger = logging.getLogger(__name__)

# RSS/Atom feed URLs for Thai news
FEEDS = {
    "bangkok_post_business": {
        "url": "https://www.bangkokpost.com/rss/data/business.xml",
        "language": "en",
        "category": "business",
    },
    "bangkok_post_tech": {
        "url": "https://www.bangkokpost.com/rss/data/tech.xml",
        "language": "en",
        "category": "technology",
    },
    "techsauce": {
        "url": "https://techsauce.co/feed",
        "language": "th",
        "category": "technology",
    },
    "thaiger_business": {
        "url": "https://thethaiger.com/news/business/feed",
        "language": "th",
        "category": "business",
    },
    "techcrunch": {
        "url": "https://techcrunch.com/feed/",
        "language": "en",
        "category": "technology",
    },
}


class ThaiNewsScraper(RSSScraper):
    """Scrape Thai news from RSS/Atom feeds."""

    def __init__(self, feed_names: Optional[List[str]] = None):
        super().__init__(
            name="thai_news",
            rate_limit=1.0,  # RSS is lightweight
        )
        self.feed_names = feed_names or list(FEEDS.keys())

    def scrape_feeds(self) -> List[NewsArticle]:
        """Parse all configured feeds and return NewsArticle objects."""
        articles = []

        for feed_name in self.feed_names:
            if feed_name not in FEEDS:
                logger.warning(f"Unknown feed: {feed_name}")
                continue

            feed_config = FEEDS[feed_name]
            feed_url = feed_config["url"]
            logger.info(f"Scraping feed: {feed_name} → {feed_url}")

            entries = self.extract_entries(feed_url)
            for entry in entries:
                article = NewsArticle(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    summary=entry.get("summary", ""),
                    author=entry.get("author", ""),
                    published_date=entry.get("published"),
                    tags=entry.get("tags", []),
                    language=feed_config["language"],
                    source=feed_name,
                    raw_data={
                        "feed_url": feed_url,
                        "feed_title": entry.get("feed_title", ""),
                        "category": feed_config["category"],
                    },
                )
                articles.append(article)
                self.add_result(article.__dict__)

            logger.info(f"  Found {len(entries)} articles from {feed_name}")

        return articles

    async def run(self, feed_names: Optional[List[str]] = None):
        """Run scraper for all configured feeds."""
        if feed_names:
            self.feed_names = feed_names

        articles = self.scrape_feeds()

        self.print_stats()
        self.export_csv("thai_news.csv")
        self.export_json("thai_news.json")
        return self.results


async def main():
    scraper = ThaiNewsScraper()
    results = await scraper.run()
    print(f"\nTotal news articles scraped: {len(results)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
