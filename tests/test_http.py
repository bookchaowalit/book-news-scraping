"""Offline tests for the shared polite fetch helper."""

import unittest
from unittest.mock import patch

import httpx

from news.http import USER_AGENT, FeedFetchError, fetch_bytes


def _response(status: int, content: bytes = b"<rss/>", headers=None) -> httpx.Response:
    request = httpx.Request("GET", "https://publisher.example/feed")
    return httpx.Response(status, content=content, headers=headers or {}, request=request)


class FetchBytesTests(unittest.TestCase):
    def test_success_sends_identifying_user_agent_and_timeout(self):
        with patch("news.http.httpx.get", return_value=_response(200)) as get:
            body = fetch_bytes("https://publisher.example/feed", source="Demo", sleep=lambda _s: None)
        self.assertEqual(body, b"<rss/>")
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["headers"]["User-Agent"], USER_AGENT)
        self.assertEqual(kwargs["timeout"], 30.0)

    def test_retries_transient_status_then_succeeds(self):
        sleeps: list[float] = []
        responses = [_response(503), _response(429, headers={"Retry-After": "5"}), _response(200)]
        with patch("news.http.httpx.get", side_effect=responses) as get:
            body = fetch_bytes("https://publisher.example/feed", source="Demo", sleep=sleeps.append)
        self.assertEqual(body, b"<rss/>")
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleeps, [2.0, 5.0])

    def test_retries_timeouts_and_gives_up(self):
        sleeps: list[float] = []
        with patch("news.http.httpx.get", side_effect=httpx.ReadTimeout("slow")) as get:
            with self.assertRaises(FeedFetchError) as ctx:
                fetch_bytes("https://publisher.example/feed", source="Demo", attempts=3, sleep=sleeps.append)
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleeps, [2.0, 4.0])
        self.assertIn("ReadTimeout", str(ctx.exception))

    def test_permanent_client_error_is_not_retried(self):
        with patch("news.http.httpx.get", return_value=_response(403)) as get:
            with self.assertRaises(httpx.HTTPStatusError):
                fetch_bytes("https://publisher.example/feed", source="Demo", sleep=lambda _s: None)
        self.assertEqual(get.call_count, 1)

    def test_retry_after_is_capped(self):
        sleeps: list[float] = []
        responses = [_response(429, headers={"Retry-After": "3600"}), _response(200)]
        with patch("news.http.httpx.get", side_effect=responses):
            fetch_bytes("https://publisher.example/feed", source="Demo", sleep=sleeps.append)
        self.assertEqual(sleeps, [60.0])

    def test_empty_body_is_rejected(self):
        with patch("news.http.httpx.get", return_value=_response(200, content=b"")):
            with self.assertRaises(ValueError):
                fetch_bytes("https://publisher.example/feed", source="Demo", sleep=lambda _s: None)


if __name__ == "__main__":
    unittest.main()
