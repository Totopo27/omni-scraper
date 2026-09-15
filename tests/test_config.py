"""Tests for strict configuration loading and validation."""

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from omni_scraper.config import BrowserConfig, OmniConfig, ScrapingConfig, load_config


class TestConfiguration(unittest.TestCase):
    def test_explicit_missing_config_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/definitely/missing/omni-scraper.yaml")

    def test_unknown_keys_and_type_coercion_are_rejected(self):
        with self.assertRaises(ValidationError):
            OmniConfig(browser={"browser_typo": "chrome"})

        with self.assertRaises(ValidationError):
            BrowserConfig(slow_mo_ms="100")

    def test_profile_dir_alias_is_supported(self):
        config = OmniConfig(browser={"profile_dir": "./custom-profile"})
        self.assertEqual(config.browser.user_data_dir, "./custom-profile")

    def test_invalid_cdp_url_is_rejected(self):
        with self.assertRaises(ValidationError):
            BrowserConfig(cdp_url="localhost:9222")

    def test_invalid_scroll_bounds_are_rejected(self):
        with self.assertRaises(ValidationError):
            ScrapingConfig(scroll_delay_min=3.0, scroll_delay_max=1.0)

    def test_yaml_root_must_be_a_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(str(config_path))


if __name__ == "__main__":
    unittest.main()
