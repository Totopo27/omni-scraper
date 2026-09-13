"""Human-like interaction simulation: organic scrolling, jitter, and natural delays."""

import random
import time
from typing import Any, Tuple


class HumanActions:
    """Provides methods to simulate human browsing patterns and avoid robotic detection."""

    def organic_sleep(self, min_seconds: float = 1.0, max_seconds: float = 2.5) -> None:
        """Sleep for a randomized duration between bounds."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def human_scroll(
        self,
        page: Any,
        target_scrolls: int = 5,
        delay_min: float = 1.0,
        delay_max: float = 2.5,
        delta_range: Tuple[int, int] = (400, 850),
    ) -> None:
        """
        Scroll down the page using variable increments and micro-pauses
        to replicate human reading behavior.
        """
        for _ in range(target_scrolls):
            delta = random.randint(delta_range[0], delta_range[1])
            # Small jitter to scroll by non-round numbers
            jitter = random.randint(-25, 25)
            scroll_amount = max(100, delta + jitter)

            page.evaluate(f"window.scrollBy({{ top: {scroll_amount}, behavior: 'smooth' }});")
            self.organic_sleep(delay_min, delay_max)

            # Check if we reached the bottom of the page
            page.evaluate("document.body.scrollHeight")
