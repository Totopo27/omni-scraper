"""HackerNews platform scraper adapter."""

from typing import Any, List
from omni_scraper.core.base_scraper import BaseScraper, ScrapedItem, ScraperRegistry
from omni_scraper.core.actions import HumanActions


class HackerNewsScraper(BaseScraper):
    """Extracts stories from HackerNews (YCombinator)."""

    platform_name: str = "hackernews"

    def __init__(self):
        self.actions = HumanActions()

    def navigate(self, page: Any, target: str = "top") -> None:
        """Navigate to HackerNews front page."""
        url = "https://news.ycombinator.com/"
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self.actions.organic_sleep(1.0, 2.0)

    def extract(self, page: Any, limit: int = 20) -> List[ScrapedItem]:
        """Extract stories up to the requested limit."""
        js_script = """
        () => {
            const results = [];
            const rows = document.querySelectorAll('tr.athing');
            rows.forEach(row => {
                const id = row.getAttribute('id') || '';
                const titleEl = row.querySelector('.titleline > a');
                const title = titleEl ? titleEl.innerText.trim() : '';
                const url = titleEl ? titleEl.getAttribute('href') : '';

                // Subtext is in the next sibling row
                const subtextRow = row.nextElementSibling;
                let score = 0;
                let author = '';
                let comments = 0;

                if (subtextRow) {
                    const scoreEl = subtextRow.querySelector('.score');
                    if (scoreEl) {
                        score = parseInt(scoreEl.innerText.replace(/[^0-9]/g, '') || '0', 10);
                    }
                    const authorEl = subtextRow.querySelector('.hnuser');
                    if (authorEl) {
                        author = authorEl.innerText.trim();
                    }
                    const commentsEl = subtextRow.querySelector('a[href*="item?id="]:last-child');
                    if (commentsEl) {
                        comments = parseInt(commentsEl.innerText.replace(/[^0-9]/g, '') || '0', 10);
                    }
                }

                if (id && title) {
                    results.push({
                        id: `hn_${id}`,
                        title: title,
                        author: author,
                        score: score,
                        comments: comments,
                        url: url
                    });
                }
            });
            return results;
        }
        """

        raw_items = page.evaluate(js_script) or []
        items: List[ScrapedItem] = []
        for raw in raw_items[:limit]:
            items.append(
                ScrapedItem(
                    item_id=str(raw.get("id")),
                    platform=self.platform_name,
                    url=raw.get("url") or "",
                    payload={
                        "title": raw.get("title", ""),
                        "author": raw.get("author", ""),
                        "score": raw.get("score", 0),
                        "comments": raw.get("comments", 0),
                    },
                )
            )

        return items


# Auto-register scraper
ScraperRegistry.register("hackernews", HackerNewsScraper)
