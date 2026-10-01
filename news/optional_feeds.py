"""Opt-in feeds from the retired ``thai_news_scraper`` roster (config only).

These are NOT in the default ``scripts/run_feeds.py`` roster: the Solo Empire
News capture (``run_news_capture.NEWS_FEEDS``) and lake ingest register only
the four contracted sources. Run them explicitly with
``scripts/run_feeds.py --feeds bangkok_post_tech`` until the parent contract
lists them.

The feed URLs come from the legacy module's configuration. Test fixtures are
synthetic documents in the standard RSS 2.0 / WordPress feed shape (the same
shape as the existing Bangkok Post and Matichon fixtures), not captures of the
live sites; confirm each live feed once before scheduling it.

Techsauce (``https://techsauce.co/feed``) is intentionally not added: its feed
format could not be confirmed offline.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from news import feed_adapter

BANGKOK_POST_TECH = feed_adapter.FeedSpec(
    key="bangkok_post_tech",
    source_name="Bangkok Post Tech",
    label="Bangkok Post Tech RSS feed",
    publisher="Bangkok Post",
    feed_url="https://www.bangkokpost.com/rss/data/tech.xml",
    host_suffix="bangkokpost.com",
    feed_paths=("/rss/data/tech.xml",),
    extras=feed_adapter.section_extras("technology"),
    extra_fields=("section",),
    # Same publisher RSS system as Business: naive pubDates are Bangkok time.
    source_timezone=ZoneInfo("Asia/Bangkok"),
)

THAIGER_BUSINESS = feed_adapter.FeedSpec(
    key="thaiger_business",
    source_name="Thaiger Business",
    label="Thaiger Business RSS feed",
    publisher="Thaiger",
    feed_url="https://thethaiger.com/news/business/feed",
    host_suffix="thethaiger.com",
    feed_paths=("/news/business/feed",),
    extras=feed_adapter.section_extras("business", topics=True),
    extra_fields=("section", "topics"),
)

TECHCRUNCH = feed_adapter.FeedSpec(
    key="techcrunch_tech",
    source_name="TechCrunch",
    label="TechCrunch RSS feed",
    publisher="TechCrunch",
    feed_url="https://techcrunch.com/feed/",
    host_suffix="techcrunch.com",
    feed_paths=("/feed",),
    extras=feed_adapter.section_extras("technology", topics=True),
    extra_fields=("section", "topics"),
)

BangkokPostTechScraper = feed_adapter.scraper_class(BANGKOK_POST_TECH, "BangkokPostTechScraper", __name__)
ThaigerBusinessScraper = feed_adapter.scraper_class(THAIGER_BUSINESS, "ThaigerBusinessScraper", __name__)
TechCrunchScraper = feed_adapter.scraper_class(TECHCRUNCH, "TechCrunchScraper", __name__)

OPTIONAL_FEEDS = (
    (BANGKOK_POST_TECH.key, BangkokPostTechScraper),
    (THAIGER_BUSINESS.key, ThaigerBusinessScraper),
    (TECHCRUNCH.key, TechCrunchScraper),
)
