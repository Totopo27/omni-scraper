"""Browser session lifecycle, sanitized stealth injection, and CDP connection management."""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import BrowserContext, Page, sync_playwright

from omni_scraper.config import BrowserConfig


SANITIZED_STEALTH_JS = """
// Set consistent navigator languages without tampering with native getters
try {
  if (!navigator.languages || navigator.languages.length === 0) {
    Object.defineProperty(navigator, 'languages', {
      get: () => ['es-ES', 'es', 'en-US', 'en'],
      configurable: true,
    });
  }
} catch (e) {}
"""


def resolve_browser_executable(browser_type: str, explicit_path: Optional[str] = None) -> Optional[str]:
    """Find the browser binary on disk or return None to let Playwright use its default."""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path

    if sys.platform == "win32":
        paths = {
            "brave": [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ],
            "chrome": [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ],
            "edge": [
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
            ],
        }
        for p in paths.get(browser_type.lower(), []):
            if os.path.exists(p):
                return p
    else:
        candidates = {
            "brave": ["brave-browser", "brave"],
            "chrome": ["google-chrome-stable", "google-chrome", "chromium-browser", "chromium"],
            "edge": ["microsoft-edge-stable", "microsoft-edge"],
        }
        for cmd in candidates.get(browser_type.lower(), []):
            found = shutil.which(cmd)
            if found:
                return found

    return explicit_path


class BrowserSession:
    """Manages a persistent Chromium session or external CDP connection with anti-detection flags."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self.profile_path = Path(config.user_data_dir).resolve()
        self.profile_path.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._browser = None

    def __enter__(self) -> Tuple[BrowserContext, Page]:
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self, override_headless: Optional[bool] = None) -> Tuple[BrowserContext, Page]:
        """Launch the persistent browser context or connect to an existing CDP endpoint."""
        headless = self.config.headless if override_headless is None else override_headless

        self._playwright = sync_playwright().start()

        # External CDP Mode (e.g. Fortress in Docker, remote Chromium, or Chrome debugging port)
        if self.config.cdp_url:
            self._browser = self._playwright.chromium.connect_over_cdp(self.config.cdp_url)
            contexts = self._browser.contexts
            self._context = contexts[0] if contexts else self._browser.new_context()
            pages = self._context.pages
            page = pages[0] if pages else self._context.new_page()
            return self._context, page

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions-except=",
            "--disable-component-update",
        ]

        executable = resolve_browser_executable(
            self.config.browser_type, self.config.executable_path
        )

        kwargs = {
            "user_data_dir": str(self.profile_path),
            "headless": headless,
            "args": args,
            "viewport": {
                "width": self.config.viewport.width,
                "height": self.config.viewport.height,
            },
            "user_agent": self.config.user_agent,
            "slow_mo": self.config.slow_mo_ms,
        }

        if executable:
            kwargs["executable_path"] = executable

        self._context = self._playwright.chromium.launch_persistent_context(**kwargs)

        # Inject passive sanitized stealth script into every new page
        if SANITIZED_STEALTH_JS.strip():
            self._context.add_init_script(SANITIZED_STEALTH_JS)

        pages = self._context.pages
        page = pages[0] if pages else self._context.new_page()
        return self._context, page

    def close(self):
        """Clean up the browser context, external connections, and Playwright driver."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
