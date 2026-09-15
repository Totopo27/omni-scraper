"""Configuration models and YAML loader for Omni-Scraper."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictConfigModel(BaseModel):
    """Base model that rejects coercion, unknown keys, and invalid assignment."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class ViewportConfig(StrictConfigModel):
    width: int = Field(default=1280, gt=0)
    height: int = Field(default=800, gt=0)


class BrowserConfig(StrictConfigModel):
    headless: bool = False
    slow_mo_ms: int = Field(default=250, ge=0)
    browser_type: Literal["brave", "chrome", "edge", "chromium"] = "brave"
    executable_path: str | None = Field(default=None, min_length=1)
    cdp_url: str | None = Field(default=None, min_length=1)
    user_data_dir: str = Field(
        default="./browser_profile",
        min_length=1,
        validation_alias=AliasChoices("user_data_dir", "profile_dir"),
    )
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        min_length=1,
    )

    @field_validator("cdp_url")
    @classmethod
    def validate_cdp_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("cdp_url must be an absolute HTTP(S) URL")
        return value


class StorageConfig(StrictConfigModel):
    db_path: str = Field(default="./data/omni_scraper.db", min_length=1)
    retention_days: int = Field(default=30, ge=0)


class ScrapingConfig(StrictConfigModel):
    max_scroll_attempts: int = Field(default=10, ge=0)
    scroll_delay_min: float = Field(default=1.0, ge=0)
    scroll_delay_max: float = Field(default=2.5, ge=0)

    @model_validator(mode="after")
    def validate_scroll_delays(self) -> "ScrapingConfig":
        if self.scroll_delay_min > self.scroll_delay_max:
            raise ValueError("scroll_delay_min must be less than or equal to scroll_delay_max")
        return self


class OmniConfig(StrictConfigModel):
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)


def load_config(config_path: str | None = None) -> OmniConfig:
    """Load and strictly validate YAML configuration, or use model defaults."""
    if config_path is None:
        path = next(
            (
                candidate
                for candidate in (Path("config.yaml"), Path("config.yml"))
                if candidate.is_file()
            ),
            None,
        )
        if path is None:
            return OmniConfig()
    else:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in configuration file {path}: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise ValueError(f"Configuration root in {path} must be a mapping")

    return OmniConfig.model_validate(dict(data))
