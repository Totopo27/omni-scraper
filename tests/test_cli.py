"""Unit tests for the CLI parser and command dispatching."""

import unittest
from omni_scraper.cli.main import build_parser
from omni_scraper.config import OmniConfig


class TestCLIParser(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_doctor_command_parsing(self):
        args = self.parser.parse_args(["doctor"])
        self.assertEqual(args.command, "doctor")

    def test_db_stats_parsing(self):
        args = self.parser.parse_args(["db", "stats"])
        self.assertEqual(args.command, "db")
        self.assertEqual(args.db_action, "stats")

    def test_db_purge_parsing(self):
        args = self.parser.parse_args(["db", "purge", "--days", "15", "--force"])
        self.assertEqual(args.command, "db")
        self.assertEqual(args.db_action, "purge")
        self.assertEqual(args.days, 15)
        self.assertTrue(args.force)

    def test_global_browser_flags_parsing(self):
        args = self.parser.parse_args([
            "--headless",
            "--cdp-url", "http://localhost:9222",
            "--browser", "chrome",
            "doctor"
        ])
        self.assertTrue(args.headless)
        self.assertEqual(args.cdp_url, "http://localhost:9222")
        self.assertEqual(args.browser, "chrome")


if __name__ == "__main__":
    unittest.main()
