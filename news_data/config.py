"""Runtime configuration for the news.v1 local API."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_NAME = "book-news-scraping"
DOMAIN = "news"
SCHEMA_VERSION = "news.v1"
LINEAGE_FILE = "lake_lineage.json"
LAKE_SOURCE = REPO_NAME
LAKE_DOMAIN = DOMAIN
LAKE_DATASET_ARTICLES = "articles"
LAKE_DATASET_HISTORY = "articles_history"
LAKE_BRONZE_SCHEMA_VERSION = "1"
LAKE_PRIVACY_CLASS = "public"
LAKE_RETENTION_CLASS = "evidence"
ID_FIELDS = ["source", "article_id"]
ID_SEP = "|"


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


FREE_ONLY = env_bool("FREE_ONLY", True)
ALLOW_PAID_PROVIDERS = env_bool("ALLOW_PAID_PROVIDERS", False)
ALLOW_EXTERNAL_WRITES = env_bool("ALLOW_EXTERNAL_WRITES", False)
ALLOW_REFRESH = env_bool("ALLOW_REFRESH", False)
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "")
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8108"))
CORS_ALLOWED_ORIGINS = tuple(
    origin.strip().rstrip("/")
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)
STALE_AFTER_HOURS = float(os.environ.get("STALE_AFTER_HOURS", "24"))
DATA_LAKE_URI = os.environ.get(
    "SOLO_EMPIRE_DATA_LAKE_URI", os.environ.get("DATA_LAKE_URI", "")
)
SOLO_EMPIRE_ROOT = os.environ.get("SOLO_EMPIRE_ROOT", "")
LAKE_READ_MODE = os.environ.get("LAKE_READ_MODE", "parquet").strip().lower()
LAKE_READ_FALLBACK = os.environ.get("LAKE_READ_FALLBACK", "error").strip().lower()

