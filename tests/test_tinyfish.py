"""Unit tests for TinyFishClient and TinyFishConfig."""

import io
import json
import os
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from omni_scraper.config import TinyFishConfig
from omni_scraper.core.tinyfish import (
    TinyFishAuthError,
    TinyFishClient,
    TinyFishError,
)


class TestTinyFishConfig(unittest.TestCase):
    def test_default_config(self):
        config = TinyFishConfig()
        self.assertIsNone(config.api_key)
        self.assertEqual(config.browser_api_url, "https://api.browser.tinyfish.ai")
        self.assertEqual(config.fetch_api_url, "https://api.fetch.tinyfish.ai")
        self.assertEqual(config.timeout_seconds, 60)

    def test_get_api_key_from_config(self):
        config = TinyFishConfig(api_key="cfg_key_123")
        self.assertEqual(config.get_api_key(), "cfg_key_123")

    @patch.dict(os.environ, {"TINYFISH_API_KEY": "env_key_456"}, clear=False)
    def test_get_api_key_from_env(self):
        config = TinyFishConfig()
        self.assertEqual(config.get_api_key(), "env_key_456")


class TestTinyFishClient(unittest.TestCase):
    def setUp(self):
        self.client = TinyFishClient(api_key="test_api_key")

    def test_missing_api_key_raises_auth_error(self):
        client = TinyFishClient(api_key=None)
        with self.assertRaises(TinyFishAuthError) as ctx:
            client.create_browser_session()
        self.assertIn("API key is missing", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_create_browser_session_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "session_id": "sess_abc123",
            "cdp_url": "wss://browser.tinyfish.ai/cdp/sess_abc123",
            "base_url": "https://browser.tinyfish.ai",
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        data = self.client.create_browser_session(url="https://example.com")
        self.assertEqual(data["session_id"], "sess_abc123")
        self.assertEqual(data["cdp_url"], "wss://browser.tinyfish.ai/cdp/sess_abc123")

        # Verify request headers and payload
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.headers.get("X-api-key"), "test_api_key")
        self.assertEqual(req.headers.get("Content-type"), "application/json")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body.get("url"), "https://example.com")

    @patch("urllib.request.urlopen")
    def test_fetch_content_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "results": [{"url": "https://news.ycombinator.com", "content": "# Hacker News"}],
            "errors": [],
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = self.client.fetch_content(["https://news.ycombinator.com"], format="markdown", ttl=3600)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["content"], "# Hacker News")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["urls"], ["https://news.ycombinator.com"])
        self.assertEqual(body["format"], "markdown")
        self.assertEqual(body["ttl"], 3600)

    @patch("urllib.request.urlopen")
    def test_http_401_raises_auth_error(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="https://api.browser.tinyfish.ai",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"message": "Invalid API key"}'),
        )
        mock_urlopen.side_effect = err

        with self.assertRaises(TinyFishAuthError) as ctx:
            self.client.create_browser_session()
        self.assertIn("authentication error (401)", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_http_500_raises_tinyfish_error(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="https://api.browser.tinyfish.ai",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b'{"message": "Server failure"}'),
        )
        mock_urlopen.side_effect = err

        with self.assertRaises(TinyFishError) as ctx:
            self.client.create_browser_session()
        self.assertIn("HTTP error (500)", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_url_error_raises_tinyfish_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(TinyFishError) as ctx:
            self.client.create_browser_session()
        self.assertIn("connection error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
