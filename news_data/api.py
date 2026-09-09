"""Local read-only HTTP API for news.v1.

The API serves committed Bronze Parquet through the shared lake adapter. It
never imports the collector or contacts a publisher during a GET request.
"""

from __future__ import annotations

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

from . import config
from .store import envelope, get_record, load_history, load_records, paginate, utc_now_iso


_LOCAL_ORIGIN_RE = re.compile(
    r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", re.I
)


def _allowed_cors_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    origin = origin.strip()
    if _LOCAL_ORIGIN_RE.match(origin) or origin in config.CORS_ALLOWED_ORIGINS:
        return origin
    return None


def _apply_cors_headers(handler: BaseHTTPRequestHandler) -> None:
    origin = _allowed_cors_origin(handler.headers.get("Origin"))
    if not origin:
        return
    handler.send_header("Access-Control-Allow-Origin", origin)
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
    handler.send_header("Access-Control-Max-Age", "600")
    handler.send_header("Vary", "Origin")


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    _apply_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(payload)


def _query_int(qs: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return int(qs.get(name, [str(default)])[0])
    except (TypeError, ValueError):
        return default


class DataProductHandler(BaseHTTPRequestHandler):
    server_version = "book-news-data-api/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:  # noqa: N802
        origin = _allowed_cors_origin(self.headers.get("Origin"))
        if not origin:
            self.send_response(403)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"error":"origin not allowed"}')
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/healthz":
            records = load_records()
            return _json_response(
                self,
                200,
                {
                    "status": "ok",
                    "repository": config.REPO_NAME,
                    "domain": config.DOMAIN,
                    "schema_version": config.SCHEMA_VERSION,
                    "data_status": records["data_status"],
                    "retrieved_at": utc_now_iso(),
                    "free_only": config.FREE_ONLY,
                    "allow_paid_providers": config.ALLOW_PAID_PROVIDERS,
                    "allow_external_writes": config.ALLOW_EXTERNAL_WRITES,
                    "allow_refresh": config.ALLOW_REFRESH,
                },
            )

        if path == "/v1/metadata":
            records = load_records()
            history = load_history()
            body = {
                "repository": config.REPO_NAME,
                "domain": config.DOMAIN,
                "schema_version": config.SCHEMA_VERSION,
                "record_count": len(records["items"]),
                "history_count": len(history["items"]),
                "records_path": records["path"],
                "history_path": history["path"],
                "records_source_kind": records.get("source_kind"),
                "history_source_kind": history.get("source_kind"),
                "api_bind": f"{config.API_HOST}:{config.API_PORT}",
                "free_only": config.FREE_ONLY,
                "allow_paid_providers": config.ALLOW_PAID_PROVIDERS,
                "allow_external_writes": config.ALLOW_EXTERNAL_WRITES,
                "allow_refresh": config.ALLOW_REFRESH,
                "lake_domain": config.LAKE_DOMAIN,
                "lake_source": config.LAKE_SOURCE,
                "lake_dataset_articles": config.LAKE_DATASET_ARTICLES,
                "lake_dataset_history": config.LAKE_DATASET_HISTORY,
                "attribution_required": True,
                "acquisition": "publisher_rss_or_atom_only",
                "read_mode": records.get("read_mode", config.LAKE_READ_MODE),
                "read_fallback": records.get("read_fallback", config.LAKE_READ_FALLBACK),
                "fallback_reason": records.get("fallback_reason"),
                "shared_adapter": "data_lake.product_adapter",
            }
            return _json_response(
                self,
                200,
                envelope(
                    items=[body],
                    data_status=records["data_status"],
                    retrieved_at=records["retrieved_at"],
                ),
            )

        if path == "/v1/records":
            records = load_records()
            page, next_cursor = paginate(
                records["items"],
                limit=_query_int(qs, "limit", 50),
                cursor=qs.get("cursor", [None])[0],
            )
            return _json_response(
                self,
                200,
                envelope(
                    items=page,
                    data_status=records["data_status"],
                    next_cursor=next_cursor,
                    retrieved_at=records["retrieved_at"],
                ),
            )

        if path.startswith("/v1/records/"):
            record_id = unquote(path[len("/v1/records/"):])
            if not record_id:
                return _json_response(
                    self,
                    400,
                    envelope(items=[], data_status="error", extra={"error": "missing record_id"}),
                )
            item = get_record(record_id)
            if item is None:
                return _json_response(
                    self,
                    404,
                    envelope(
                        items=[],
                        data_status="not_found",
                        extra={"error": "record not found", "record_id": record_id},
                    ),
                )
            records = load_records()
            return _json_response(
                self,
                200,
                envelope(
                    items=[item],
                    data_status=records["data_status"],
                    retrieved_at=records["retrieved_at"],
                ),
            )

        if path == "/v1/history":
            history = load_history()
            page, next_cursor = paginate(
                history["items"],
                limit=_query_int(qs, "limit", 50),
                cursor=qs.get("cursor", [None])[0],
            )
            return _json_response(
                self,
                200,
                envelope(
                    items=page,
                    data_status=history["data_status"],
                    next_cursor=next_cursor,
                    retrieved_at=history["retrieved_at"],
                ),
            )

        return _json_response(
            self,
            404,
            envelope(items=[], data_status="not_found", extra={"error": "unknown endpoint"}),
        )

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/v1/refresh":
            return _json_response(
                self,
                404,
                envelope(items=[], data_status="not_found", extra={"error": "unknown endpoint"}),
            )
        # Collection is an explicit operator action. The API remains read-only
        # by default and never triggers a publisher request from this handler.
        auth = self.headers.get("Authorization", "")
        token = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else ""
        allowed = config.ALLOW_REFRESH and bool(config.REFRESH_TOKEN) and token == config.REFRESH_TOKEN
        if not allowed:
            return _json_response(
                self,
                403,
                envelope(
                    items=[],
                    data_status="forbidden",
                    extra={"error": "refresh disabled"},
                ),
            )
        return _json_response(
            self,
            202,
            envelope(
                items=[{"accepted": True, "action": "refresh_acknowledged"}],
                data_status="accepted",
            ),
        )


def create_server(host: Optional[str] = None, port: Optional[int] = None) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host or config.API_HOST, port if port is not None else config.API_PORT),
        DataProductHandler,
    )


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Local read-only API for book-news-scraping")
    parser.add_argument("--host", default=config.API_HOST)
    parser.add_argument("--port", type=int, default=config.API_PORT)
    args = parser.parse_args(argv)
    server = create_server(args.host, args.port)
    print(f"[{config.REPO_NAME}] API listening on http://{args.host}:{args.port}")
    print("  GET /healthz /v1/metadata /v1/records /v1/records/{id} /v1/history")
    print("  POST /v1/refresh (403 by default)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

