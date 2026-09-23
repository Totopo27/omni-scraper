"""Reddit platform scraper adapter."""

from typing import Any, List
from omni_scraper.core.base_scraper import BaseScraper, ScrapedItem, ScraperRegistry
from omni_scraper.core.actions import HumanActions


class RedditScraper(BaseScraper):
    """Extracts posts from subreddits using modern shreddit tags and organic scrolling."""

    platform_name: str = "reddit"

    def __init__(self):
        self.actions = HumanActions()

    def navigate(self, page: Any, target: str) -> None:
        """Navigate to the target subreddit."""
        clean_target = target.strip("/").replace("r/", "")
        url = f"https://www.reddit.com/r/{clean_target}/hot/"
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self.actions.organic_sleep(1.5, 3.0)

    def extract(self, page: Any, limit: int = 20) -> List[ScrapedItem]:
        """Extract posts up to the requested limit, scrolling if needed."""
        # Optional wait for Reddit main container or posts to mount
        try:
            page.wait_for_selector("shreddit-post, article, div[data-testid='post-container']", timeout=5000)
        except Exception:
            pass

        # Optional scroll to load more posts if limit > 5
        scroll_passes = max(1, (limit // 8))
        self.actions.human_scroll(page, target_scrolls=scroll_passes, delay_min=1.0, delay_max=2.0)

        js_script = """
        () => {
            const results = [];
            // Strategy A: Modern Reddit custom web components (<shreddit-post>)
            const shredditPosts = document.querySelectorAll('shreddit-post');
            if (shredditPosts.length > 0) {
                shredditPosts.forEach(post => {
                    const id = post.getAttribute('id') || post.getAttribute('data-ks-id') || '';
                    const title = post.getAttribute('post-title') || '';
                    const author = post.getAttribute('author') || '';
                    const score = parseInt(post.getAttribute('score') || '0', 10);
                    const commentCount = parseInt(post.getAttribute('comment-count') || '0', 10);
                    const permalink = post.getAttribute('permalink') || '';
                    const fullUrl = permalink ? (permalink.startsWith('http') ? permalink : 'https://www.reddit.com' + permalink) : '';

                    if (id && title) {
                        results.push({
                            id: id,
                            title: title,
                            author: author,
                            score: score,
                            comments: commentCount,
                            url: fullUrl
                        });
                    }
                });
                return results;
            }

            // Strategy B: Fallback to article elements or post containers
            const articles = document.querySelectorAll('article, div[data-testid="post-container"]');
            articles.forEach((art, idx) => {
                const titleEl = art.querySelector('h1, h2, h3, a[data-click-id="body"]');
                const title = titleEl ? titleEl.innerText.trim() : '';
                const authorEl = art.querySelector('a[href*="/user/"]');
                const author = authorEl ? authorEl.innerText.replace('u/', '').trim() : '';
                const linkEl = art.querySelector('a[href*="/comments/"]');
                const href = linkEl ? linkEl.getAttribute('href') : '';
                const fullUrl = href ? (href.startsWith('http') ? href : 'https://www.reddit.com' + href) : '';
                const id = art.getAttribute('id') || `reddit_post_${idx}`;

                if (title) {
                    results.push({
                        id: id,
                        title: title,
                        author: author,
                        score: 0,
                        comments: 0,
                        url: fullUrl
                    });
                }
            });
            return results;
        }
        """

        raw_items = page.evaluate(js_script) or []
        items: List[ScrapedItem] = []
        for raw in raw_items[:limit]:
            item_id = str(raw.get("id") or f"reddit_{len(items)}")
            items.append(
                ScrapedItem(
                    item_id=item_id,
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
ScraperRegistry.register("reddit", RedditScraper)
