"""Tests for the generic SQLite storage repository with deduplication and purging."""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from omni_scraper.core.base_scraper import ScrapedItem
from omni_scraper.storage.db import SQLiteRepository


class TestSQLiteRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_omni.db")
        self.repo = SQLiteRepository(self.db_path)

    def tearDown(self):
        self.repo.close()
        self.temp_dir.cleanup()

    def test_tables_created_on_init(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        self.assertIn("scraped_items", tables)
        self.assertIn("scrape_runs", tables)

    def test_insert_items_and_deduplication(self):
        items = [
            ScrapedItem(
                item_id="item-1",
                platform="reddit",
                url="https://reddit.com/r/python/1",
                payload={"title": "Python 3.13 released", "score": 450},
            ),
            ScrapedItem(
                item_id="item-2",
                platform="reddit",
                url="https://reddit.com/r/python/2",
                payload={"title": "FastAPI tips", "score": 120},
            ),
        ]

        inserted = self.repo.insert_items(items)
        self.assertEqual(inserted, 2)

        # Duplicate insertion attempt
        duplicated = self.repo.insert_items(items)
        self.assertEqual(duplicated, 0)

        # Fetch and verify
        fetched = self.repo.get_items(platform="reddit")
        self.assertEqual(len(fetched), 2)
        items_by_id = {item["item_id"]: item for item in fetched}
        self.assertIn("item-1", items_by_id)
        self.assertIn("item-2", items_by_id)
        self.assertEqual(items_by_id["item-1"]["payload"]["score"], 450)
        self.assertEqual(items_by_id["item-2"]["payload"]["score"], 120)

    def test_record_run_and_get_runs(self):
        run_id = self.repo.record_run(
            run_type="reddit_scrape",
            status="success",
            items_count=2,
            metadata={"target": "r/python"},
        )
        self.assertIsInstance(run_id, int)

        runs = self.repo.get_runs(limit=5)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["run_type"], "reddit_scrape")
        self.assertEqual(runs[0]["items_count"], 2)

    def test_get_stats(self):
        items = [
            ScrapedItem(
                item_id="a1",
                platform="linkedin",
                url="https://linkedin.com/1",
                payload={"author": "alice"},
            ),
            ScrapedItem(
                item_id="b1",
                platform="reddit",
                url="https://reddit.com/1",
                payload={"author": "bob"},
            ),
        ]
        self.repo.insert_items(items)

        stats = self.repo.get_stats()
        self.assertEqual(stats["total_items"], 2)
        self.assertIn("linkedin", stats["platforms"])
        self.assertIn("reddit", stats["platforms"])

    def test_purge_older_than(self):
        # Insert item with old timestamp
        old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        item = ScrapedItem(
            item_id="old-1",
            platform="reddit",
            url="https://reddit.com/old",
            payload={"title": "Ancient news"},
            scraped_at=old_time,
        )
        self.repo.insert_items([item])

        fresh_item = ScrapedItem(
            item_id="new-1",
            platform="reddit",
            url="https://reddit.com/new",
            payload={"title": "Fresh news"},
        )
        self.repo.insert_items([fresh_item])

        purged = self.repo.purge_older_than(days=30)
        self.assertEqual(purged, 1)

        remaining = self.repo.get_items()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["item_id"], "new-1")


if __name__ == "__main__":
    unittest.main()
