"""TinyFish API client for Cloud CDP sessions and content fetching."""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class TinyFishError(Exception):
    """Base exception for TinyFish API errors."""
    pass


class TinyFishAuthError(TinyFishError):
    """Exception raised when authentication fails (HTTP 401/403)."""
    pass


class TinyFishClient:
    """Client for TinyFish Browser and Fetch APIs using urllib."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        browser_api_url: str = "https://api.browser.tinyfish.ai",
        fetch_api_url: str = "https://api.fetch.tinyfish.ai",
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key
        self.browser_api_url = browser_api_url.rstrip("/")
        self.fetch_api_url = fetch_api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TinyFishAuthError("TinyFish API key is missing. Set TINYFISH_API_KEY or configure api_key.")
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "User-Agent": "OmniScraper/TinyFishClient",
        }

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = self._get_headers()
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw_body = resp.read().decode("utf-8")
                return json.loads(raw_body) if raw_body else {}
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code in (401, 403):
                raise TinyFishAuthError(
                    f"TinyFish authentication error ({e.code}): {e.reason}. {error_body}".strip()
                ) from e
            raise TinyFishError(
                f"TinyFish HTTP error ({e.code}): {e.reason}. {error_body}".strip()
            ) from e
        except urllib.error.URLError as e:
            raise TinyFishError(f"TinyFish connection error: {e.reason}") from e
        except Exception as e:
            raise TinyFishError(f"Unexpected error communicating with TinyFish: {e}") from e

    def create_browser_session(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Create a cloud browser session via TinyFish Browser API.

        Returns dict containing session_id, cdp_url, base_url (or other metadata returned by API).
        """
        payload: Dict[str, Any] = {}
        if url:
            payload["url"] = url
        return self._post(self.browser_api_url, payload)

    def fetch_content(
        self,
        urls: List[str],
        format: str = "markdown",
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch clean content (markdown, html, json) via TinyFish Fetch API.

        Returns dict with results and errors.
        """
        payload: Dict[str, Any] = {
            "urls": urls,
            "format": format,
        }
        if ttl is not None:
            payload["ttl"] = ttl
        return self._post(self.fetch_api_url, payload)
