"""Generic SQLite repository with atomic deduplication, run logging, and retention purging."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from omni_scraper.core.base_scraper import ScrapedItem


class SQLiteRepository:
    """Persistent storage engine for scraped items and execution logs."""

    def __init__(self, db_path: str = "./data/omni_scraper.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            self._conn.row_factory = sqlite3.Row
            # WAL mode for high concurrency and resilience
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA busy_timeout=5000;")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scraped_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    url TEXT,
                    payload TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    UNIQUE(platform, item_id)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_items_platform 
                ON scraped_items(platform);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_items_scraped_at 
                ON scraped_items(scraped_at);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def insert_items(self, items: List[ScrapedItem]) -> int:
        """Insert items into the database. Skips items that already exist. Returns inserted count."""
        if not items:
            return 0

        conn = self._get_connection()
        inserted_count = 0
        with conn:
            for item in items:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO scraped_items (platform, item_id, url, payload, scraped_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        item.platform,
                        item.item_id,
                        item.url,
                        json.dumps(item.payload, ensure_ascii=False),
                        item.scraped_at,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted_count += 1

        return inserted_count

    def get_items(self, platform: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve items, optionally filtered by platform."""
        conn = self._get_connection()
        query = "SELECT platform, item_id, url, payload, scraped_at FROM scraped_items"
        params = []
        if platform:
            query += " WHERE platform = ?"
            params.append(platform)

        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "platform": r["platform"],
                "item_id": r["item_id"],
                "url": r["url"],
                "payload": json.loads(r["payload"]),
                "scraped_at": r["scraped_at"],
            })
        return results

    def record_run(
        self,
        run_type: str,
        status: str,
        items_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record an execution run for auditability."""
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO scrape_runs (run_type, status, items_count, metadata, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    run_type,
                    status,
                    items_count,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            return cursor.lastrowid

    def get_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve execution history."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT id, run_type, status, items_count, metadata, created_at
            FROM scrape_runs ORDER BY id DESC LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "run_type": r["run_type"],
                "status": r["status"],
                "items_count": r["items_count"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate metrics on storage volume and platforms."""
        conn = self._get_connection()
        total_items = conn.execute("SELECT COUNT(*) FROM scraped_items;").fetchone()[0]
        platforms_cursor = conn.execute(
            "SELECT platform, COUNT(*) as count FROM scraped_items GROUP BY platform;"
        )
        platforms = {r["platform"]: r["count"] for r in platforms_cursor.fetchall()}
        total_runs = conn.execute("SELECT COUNT(*) FROM scrape_runs;").fetchone()[0]

        file_size_bytes = 0
        if self.db_path.exists():
            file_size_bytes = os.path.getsize(self.db_path)

        return {
            "db_path": str(self.db_path),
            "file_size_bytes": file_size_bytes,
            "total_items": total_items,
            "platforms": platforms,
            "total_runs": total_runs,
        }

    def purge_older_than(self, days: int) -> int:
        """Purge items older than N days and perform VACUUM to reclaim disk space."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            DELETE FROM scraped_items 
            WHERE datetime(scraped_at) < datetime('now', '-' || ? || ' days');
            """,
            (str(days),),
        )
        deleted_count = cursor.rowcount
        conn.commit()

        if deleted_count > 0:
            conn.execute("VACUUM;")

        return deleted_count

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
