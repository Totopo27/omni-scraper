"""Configuration models and YAML loader for Omni-Scraper."""

import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field


class ViewportConfig(BaseModel):
    width: int = 1280
    height: int = 800


class TinyFishConfig(BaseModel):
    api_key: Optional[str] = None
    browser_api_url: str = "https://api.browser.tinyfish.ai"
    fetch_api_url: str = "https://api.fetch.tinyfish.ai"
    timeout_seconds: int = 60

    def get_api_key(self) -> Optional[str]:
        """Resolve API key from explicit config or TINYFISH_API_KEY environment variable."""
        return self.api_key or os.environ.get("TINYFISH_API_KEY")


class BrowserConfig(BaseModel):
    provider: str = "local"  # "local" or "tinyfish"
    headless: bool = False
    slow_mo_ms: int = 250
    browser_type: str = "brave"  # brave, chrome, edge, chromium
    executable_path: Optional[str] = None
    cdp_url: Optional[str] = None  # e.g. "http://localhost:9222"
    user_data_dir: str = "./browser_profile"
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )


class StorageConfig(BaseModel):
    db_path: str = "./data/omni_scraper.db"
    retention_days: int = 30


class ScrapingConfig(BaseModel):
    max_scroll_attempts: int = 10
    scroll_delay_min: float = 1.0
    scroll_delay_max: float = 2.5


class OmniConfig(BaseModel):
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    tinyfish: TinyFishConfig = Field(default_factory=TinyFishConfig)


def load_config(config_path: Optional[str] = None) -> OmniConfig:
    """Load configuration from a YAML file or fallback to defaults."""
    if not config_path:
        default_paths = [
            Path("./config.yaml"),
            Path("./config.yml"),
            Path("./config.example.yaml"),
        ]
        for p in default_paths:
            if p.is_file():
                config_path = str(p)
                break

    if config_path and Path(config_path).is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return OmniConfig(**data)

    return OmniConfig()
