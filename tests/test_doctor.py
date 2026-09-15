"""Tests for pre-flight diagnostics and failure reporting."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_scraper.config import OmniConfig
from omni_scraper.doctor.preflight import (
    check_cdp_connectivity,
    check_directory_writable,
    run_doctor,
)


class FakeHttpResponse(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200):
        super().__init__(body)
        self.status = status


class TestDoctor(unittest.TestCase):
    def test_cdp_check_requires_websocket_metadata(self):
        response = FakeHttpResponse(b'{"Browser": "not-enough"}')
        with patch("urllib.request.urlopen", return_value=response):
            ok, _ = check_cdp_connectivity("http://localhost:9222")
        self.assertFalse(ok)

    def test_cdp_check_accepts_valid_websocket_metadata(self):
        response = FakeHttpResponse(
            b'{"webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/abc"}'
        )
        with patch("urllib.request.urlopen", return_value=response):
            ok, _ = check_cdp_connectivity("http://localhost:9222")
        self.assertTrue(ok)

    def test_directory_check_does_not_delete_preexisting_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            marker = Path(temp_dir) / ".write_test"
            marker.write_text("keep", encoding="utf-8")

            ok, _ = check_directory_writable(temp_dir)

            self.assertTrue(ok)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_missing_browser_makes_doctor_fail(self):
        with (
            patch(
                "omni_scraper.doctor.preflight.check_browser_binary",
                return_value=(False, "missing"),
            ),
            patch(
                "omni_scraper.doctor.preflight.check_directory_writable",
                return_value=(True, "writable"),
            ),
            patch(
                "omni_scraper.doctor.preflight.check_database_health",
                return_value=(True, "healthy"),
            ),
            patch("omni_scraper.doctor.preflight.console"),
        ):
            self.assertFalse(run_doctor(OmniConfig()))


if __name__ == "__main__":
    unittest.main()
