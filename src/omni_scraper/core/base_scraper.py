"""Base abstractions and domain models for platform scrapers."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ScrapedItem(BaseModel):
    """Universal representation of an extracted entity."""

    item_id: str
    platform: str
    url: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ScrapeResult(BaseModel):
    """Summary of a scraping session."""

    items: List[ScrapedItem] = Field(default_factory=list)
    total_found: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = Field(default_factory=list)


class BaseScraper(ABC):
    """Contract that every platform scraper must fulfill."""

    platform_name: str = "generic"

    @abstractmethod
    def navigate(self, page: Any, target: str) -> None:
        """Navigate the browser page to the target destination."""
        pass

    @abstractmethod
    def extract(self, page: Any, limit: int = 20) -> List[ScrapedItem]:
        """Extract items from the active page up to the requested limit."""
        pass


class ScraperRegistry:
    """Registry to register and dynamically discover platform scrapers."""

    _registry: Dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, platform_name: str, scraper_cls: Type[BaseScraper]) -> None:
        cls._registry[platform_name.lower()] = scraper_cls

    @classmethod
    def get(cls, platform_name: str) -> Optional[Type[BaseScraper]]:
        return cls._registry.get(platform_name.lower())

    @classmethod
    def available_platforms(cls) -> List[str]:
        return list(cls._registry.keys())
