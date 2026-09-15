"""Pre-flight diagnostic routines to verify browser, CDP endpoints, and storage."""

import json
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Tuple
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.table import Table

from omni_scraper.config import OmniConfig
from omni_scraper.core.session import resolve_browser_executable
from omni_scraper.storage.db import SQLiteRepository

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def check_browser_binary(config: OmniConfig) -> Tuple[bool, str]:
    """Check if the configured browser executable or default is available."""
    if config.browser.cdp_url:
        return True, f"Modo CDP activo ({config.browser.cdp_url}), no requiere binario local"

    if config.browser.executable_path and not Path(config.browser.executable_path).is_file():
        return False, f"El ejecutable configurado no existe: {config.browser.executable_path}"

    resolved = resolve_browser_executable(
        config.browser.browser_type, config.browser.executable_path
    )
    if resolved and Path(resolved).is_file():
        return True, f"Encontrado: {resolved}"

    try:
        with sync_playwright() as playwright:
            managed_browser = Path(playwright.chromium.executable_path)
        if managed_browser.is_file():
            return True, f"Chromium administrado por Playwright: {managed_browser}"
    except Exception as exc:
        return False, f"No se pudo comprobar Chromium de Playwright: {exc}"

    return False, f"No se encontró un navegador utilizable para '{config.browser.browser_type}'"


def check_cdp_connectivity(cdp_url: str) -> Tuple[bool, str]:
    """Check that the endpoint exposes valid Chrome DevTools metadata."""
    try:
        req = urllib.request.Request(
            f"{cdp_url.rstrip('/')}/json/version",
            headers={"User-Agent": "OmniScraperDoctor"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status != 200:
                return False, f"CDP respondió con HTTP {resp.status} desde {cdp_url}"

            metadata = json.load(resp)
            websocket_url = (
                metadata.get("webSocketDebuggerUrl")
                if isinstance(metadata, dict)
                else None
            )
            websocket_endpoint = urlsplit(websocket_url) if isinstance(websocket_url, str) else None
            if (
                websocket_endpoint is None
                or websocket_endpoint.scheme not in {"ws", "wss"}
                or not websocket_endpoint.netloc
            ):
                return False, f"La respuesta de {cdp_url} no contiene un endpoint CDP válido"

            return True, f"Conexión CDP validada en {cdp_url}"
    except Exception as e:
        return False, f"No se pudo conectar a {cdp_url}: {e}"


def check_directory_writable(dir_path: str) -> Tuple[bool, str]:
    """Verify that a directory is writable."""
    p = Path(dir_path).resolve()
    try:
        p.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".omni_scraper_write_test_", dir=p):
            pass
        return True, f"Permisos de escritura OK: {p}"
    except Exception as e:
        return False, f"Error de escritura en {p}: {e}"


def check_database_health(db_path: str) -> Tuple[bool, str]:
    """Verify database initialization and query execution."""
    repo = None
    try:
        repo = SQLiteRepository(db_path)
        stats = repo.get_stats()
        return True, f"Base de datos accesible. Total ítems: {stats['total_items']}"
    except Exception as e:
        return False, f"Fallo al conectar con la base de datos: {e}"
    finally:
        if repo is not None:
            repo.close()


def run_doctor(config: OmniConfig) -> bool:
    """Run all pre-flight checks and display a rich diagnostic table."""
    table = Table(title="🏥 Omni-Scraper Pre-Flight Diagnostics")
    table.add_column("Componente", style="cyan", no_wrap=True)
    table.add_column("Estado", justify="center")
    table.add_column("Detalle", style="dim")

    all_ok = True

    # 1. Browser Binary Check
    b_ok, b_msg = check_browser_binary(config)
    all_ok = all_ok and b_ok
    table.add_row("Navegador Local", "✅ OK" if b_ok else "❌ ERROR", b_msg)

    # 2. CDP Connectivity (if configured)
    if config.browser.cdp_url:
        cdp_ok, cdp_msg = check_cdp_connectivity(config.browser.cdp_url)
        all_ok = all_ok and cdp_ok
        table.add_row("Endpoint CDP", "✅ OK" if cdp_ok else "❌ ERROR", cdp_msg)

    # 3. Profile Directory
    prof_ok, prof_msg = check_directory_writable(config.browser.user_data_dir)
    all_ok = all_ok and prof_ok
    table.add_row("Perfil Persistente", "✅ OK" if prof_ok else "❌ ERROR", prof_msg)

    # 4. Storage Directory & DB
    db_dir = Path(config.storage.db_path).parent
    db_dir_ok, db_dir_msg = check_directory_writable(str(db_dir))
    all_ok = all_ok and db_dir_ok
    table.add_row("Directorio Data", "✅ OK" if db_dir_ok else "❌ ERROR", db_dir_msg)

    db_ok, db_msg = check_database_health(config.storage.db_path)
    all_ok = all_ok and db_ok
    table.add_row("Base SQLite", "✅ OK" if db_ok else "❌ ERROR", db_msg)

    console.print(table)
    return all_ok
