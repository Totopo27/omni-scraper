"""Unit tests for BrowserSession, anti-detection flags, and CDP connection."""

import os
import unittest
from unittest.mock import MagicMock, patch

from omni_scraper.config import BrowserConfig
from omni_scraper.core.session import BrowserSession, SANITIZED_STEALTH_JS, resolve_browser_executable


class TestBrowserSession(unittest.TestCase):
    def test_sanitized_stealth_script_hygiene(self):
        """Ensure stealth script does not tamper with native webdriver or window.chrome."""
        self.assertNotIn("navigator.webdriver", SANITIZED_STEALTH_JS)
        self.assertNotIn("window.chrome", SANITIZED_STEALTH_JS)
        self.assertIn("navigator.languages", SANITIZED_STEALTH_JS)

    @patch("omni_scraper.core.session.sync_playwright")
    def test_start_local_persistent_context(self, mock_playwright):
        mock_pw = MagicMock()
        mock_playwright.return_value.start.return_value = mock_pw
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.pages = [mock_page]
        mock_pw.chromium.launch_persistent_context.return_value = mock_context

        config = BrowserConfig(
            headless=True,
            user_data_dir="./test_profile",
            cdp_url=None,
        )
        session = BrowserSession(config)

        context, page = session.start()

        self.assertEqual(context, mock_context)
        self.assertEqual(page, mock_page)
        mock_pw.chromium.launch_persistent_context.assert_called_once()
        kwargs = mock_pw.chromium.launch_persistent_context.call_args[1]
        self.assertIn("--disable-blink-features=AutomationControlled", kwargs["args"])
        mock_context.add_init_script.assert_called_once()

        session.close()
        mock_context.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    @patch("omni_scraper.core.session.sync_playwright")
    def test_start_external_cdp_connection(self, mock_playwright):
        mock_pw = MagicMock()
        mock_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_pw.chromium.connect_over_cdp.return_value = mock_browser

        config = BrowserConfig(
            cdp_url="http://localhost:9222",
        )
        session = BrowserSession(config)

        context, page = session.start()

        self.assertEqual(context, mock_context)
        self.assertEqual(page, mock_page)
        mock_pw.chromium.connect_over_cdp.assert_called_once_with("http://localhost:9222")
        mock_pw.chromium.launch_persistent_context.assert_not_called()

        session.close()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_resolve_browser_executable_fallback(self):
        # Even with nonexistent explicit path, fallback or None is returned cleanly
        resolved = resolve_browser_executable("chromium", "non_existent_binary.exe")
        self.assertEqual(resolved, "non_existent_binary.exe")


if __name__ == "__main__":
    unittest.main()
