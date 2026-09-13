"""Unit tests for platform scrapers (Reddit, HackerNews) and registry."""

import unittest
from unittest.mock import MagicMock

from omni_scraper.core.base_scraper import ScraperRegistry
from omni_scraper.scrapers.reddit import RedditScraper
from omni_scraper.scrapers.hackernews import HackerNewsScraper


class TestPlatformScrapers(unittest.TestCase):
    def test_scrapers_registered(self):
        self.assertIn("reddit", ScraperRegistry.available_platforms())
        self.assertIn("hackernews", ScraperRegistry.available_platforms())
        self.assertEqual(ScraperRegistry.get("reddit"), RedditScraper)
        self.assertEqual(ScraperRegistry.get("hackernews"), HackerNewsScraper)

    def test_reddit_scraper_navigate(self):
        scraper = RedditScraper()
        mock_page = MagicMock()
        scraper.navigate(mock_page, "artificial")
        mock_page.goto.assert_called_once_with(
            "https://www.reddit.com/r/artificial/hot/",
            wait_until="domcontentloaded",
            timeout=30000,
        )

    def test_reddit_scraper_extract(self):
        scraper = RedditScraper()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = [
            {
                "id": "t3_123",
                "title": "Anthropic releases new model",
                "author": "tech_fan",
                "score": 450,
                "comments": 80,
                "url": "https://www.reddit.com/r/artificial/comments/123/",
            },
            {
                "id": "t3_456",
                "title": "Local LLM breakthrough",
                "author": "coder_pro",
                "score": 890,
                "comments": 150,
                "url": "https://www.reddit.com/r/artificial/comments/456/",
            },
        ]

        items = scraper.extract(mock_page, limit=5)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].platform, "reddit")
        self.assertEqual(items[0].item_id, "t3_123")
        self.assertEqual(items[0].payload["title"], "Anthropic releases new model")
        self.assertEqual(items[0].payload["score"], 450)

    def test_hackernews_scraper_navigate(self):
        scraper = HackerNewsScraper()
        mock_page = MagicMock()
        scraper.navigate(mock_page, "top")
        mock_page.goto.assert_called_once_with(
            "https://news.ycombinator.com/",
            wait_until="domcontentloaded",
            timeout=30000,
        )

    def test_hackernews_scraper_extract(self):
        scraper = HackerNewsScraper()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = [
            {
                "id": "hn_999",
                "title": "Show HN: Omni-Scraper in Python",
                "author": "builder",
                "score": 150,
                "comments": 42,
                "url": "https://news.ycombinator.com/item?id=999",
            }
        ]

        items = scraper.extract(mock_page, limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform, "hackernews")
        self.assertEqual(items[0].item_id, "hn_999")
        self.assertEqual(items[0].payload["score"], 150)


if __name__ == "__main__":
    unittest.main()
