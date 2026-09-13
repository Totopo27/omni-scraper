"""Unit tests for HumanActions and organic behavioral simulation."""

import unittest
from unittest.mock import MagicMock, patch

from omni_scraper.core.actions import HumanActions


class TestHumanActions(unittest.TestCase):
    @patch("time.sleep")
    def test_organic_sleep(self, mock_sleep):
        actions = HumanActions()
        actions.organic_sleep(min_seconds=0.5, max_seconds=1.0)
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(sleep_arg, 0.5)
        self.assertLessEqual(sleep_arg, 1.0)

    @patch("time.sleep")
    def test_human_scroll(self, mock_sleep):
        mock_page = MagicMock()
        mock_page.evaluate.return_value = 1000  # scroll height

        actions = HumanActions()
        actions.human_scroll(
            page=mock_page,
            target_scrolls=3,
            delay_min=0.1,
            delay_max=0.2,
        )

        # Should have called evaluate multiple times (scrollBy and document height checks)
        self.assertGreaterEqual(mock_page.evaluate.call_count, 3)
        self.assertGreaterEqual(mock_sleep.call_count, 3)


if __name__ == "__main__":
    unittest.main()
