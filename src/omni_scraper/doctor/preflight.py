"""Pre-flight diagnostic routines to verify browser, CDP endpoints, and storage."""

import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple
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

    resolved = resolve_browser_executable(
        config.browser.browser_type, config.browser.executable_path
    )
    if resolved and os.path.exists(resolved):
        return True, f"Encontrado: {resolved}"
    return False, f"No se encontró binario para '{config.browser.browser_type}'. Usará fallback de Playwright si está instalado."


def check_cdp_connectivity(cdp_url: str) -> Tuple[bool, str]:
    """Check if the external CDP endpoint is reachable."""
    try:
        req = urllib.request.Request(f"{cdp_url.rstrip('/')}/json/version", headers={"User-Agent": "OmniScraperDoctor"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                return True, f"Conexión exitosa a CDP en {cdp_url}"
    except Exception as e:
        return False, f"No se pudo conectar a {cdp_url}: {e}"
    return False, f"Respuesta no esperada desde {cdp_url}"


def check_directory_writable(dir_path: str) -> Tuple[bool, str]:
    """Verify that a directory is writable."""
    p = Path(dir_path).resolve()
    try:
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        return True, f"Permisos de escritura OK: {p}"
    except Exception as e:
        return False, f"Error de escritura en {p}: {e}"


def check_database_health(db_path: str) -> Tuple[bool, str]:
    """Verify database initialization and query execution."""
    try:
        repo = SQLiteRepository(db_path)
        stats = repo.get_stats()
        repo.close()
        return True, f"Base de datos accesible. Total ítems: {stats['total_items']}"
    except Exception as e:
        return False, f"Fallo al conectar con la base de datos: {e}"


def check_tinyfish_status(config: OmniConfig) -> Tuple[bool, str]:
    """Check if TinyFish configuration is valid when key or provider is present."""
    api_key = config.tinyfish.get_api_key()
    is_provider = config.browser.provider == "tinyfish"

    if not api_key and not is_provider:
        return True, "No configurado (opcional)"

    if is_provider and not api_key:
        return False, "Provider es 'tinyfish' pero TINYFISH_API_KEY no está configurada"

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key or "") > 8 else "***"
    return True, f"Configurado (Key: {masked_key}, Browser: {config.tinyfish.browser_api_url})"


def run_doctor(config: OmniConfig) -> bool:
    """Run all pre-flight checks and display a rich diagnostic table."""
    table = Table(title="🏥 Omni-Scraper Pre-Flight Diagnostics")
    table.add_column("Componente", style="cyan", no_wrap=True)
    table.add_column("Estado", justify="center")
    table.add_column("Detalle", style="dim")

    all_ok = True

    # 1. Browser Binary Check
    b_ok, b_msg = check_browser_binary(config)
    table.add_row("Navegador Local", "✅ OK" if b_ok else "⚠️ AVISO", b_msg)

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

    # 5. TinyFish Integration Check (if configured or enabled)
    tf_ok, tf_msg = check_tinyfish_status(config)
    all_ok = all_ok and tf_ok
    table.add_row("TinyFish API", "✅ OK" if tf_ok else "❌ ERROR", tf_msg)

    console.print(table)
    return all_ok
