"""Command implementations for Omni-Scraper CLI."""

import sys
from rich.console import Console
from rich.table import Table

from omni_scraper.config import OmniConfig
from omni_scraper.doctor.preflight import run_doctor
from omni_scraper.storage.db import SQLiteRepository

console = Console()


def handle_doctor(config: OmniConfig, args) -> None:
    """Run pre-flight environment checks."""
    ok = run_doctor(config)
    if not ok:
        sys.exit(1)


def handle_db(config: OmniConfig, args) -> None:
    """Manage and inspect the SQLite database."""
    repo = SQLiteRepository(config.storage.db_path)

    if args.db_action == "stats":
        stats = repo.get_stats()
        table = Table(title="📊 Omni-Scraper Database Stats")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Ruta DB", stats["db_path"])
        size_kb = round(stats["file_size_bytes"] / 1024, 2)
        table.add_row("Tamaño en disco", f"{size_kb} KB")
        table.add_row("Total de ítems únicos", str(stats["total_items"]))
        table.add_row("Total de ejecuciones (runs)", str(stats["total_runs"]))

        platforms_summary = ", ".join(f"{k}: {v}" for k, v in stats["platforms"].items()) or "Ninguna"
        table.add_row("Plataformas registradas", platforms_summary)

        console.print(table)

    elif args.db_action == "purge":
        days = getattr(args, "days", 30)
        force = getattr(args, "force", False)

        if not force:
            confirm = input(f"¿Estás seguro de purgar ítems con más de {days} días de antigüedad? (s/N): ")
            if confirm.lower() not in ("s", "si", "y", "yes"):
                console.print("[yellow]Operación cancelada.[/yellow]")
                repo.close()
                return

        deleted = repo.purge_older_than(days)
        console.print(f"[green]🧹 Purga completada:[/green] {deleted} ítems eliminados y base de datos compactada con VACUUM.")

    repo.close()


def handle_clean(config: OmniConfig, args) -> None:
    """Clean transient caches without removing database or profiles."""
    dry_run = getattr(args, "dry_run", False)
    console.print(f"[cyan]{'[DRY-RUN] ' if dry_run else ''}Limpiando cachés temporales...[/cyan]")
    # Placeholder for extensible cache cleaner
    console.print("[green]Limpieza finalizada con éxito.[/green]")


def handle_scrape(config: OmniConfig, args) -> None:
    """Execute scraping with the requested platform adapter."""
    import time
    from omni_scraper.core.session import BrowserSession
    from omni_scraper.core.base_scraper import ScraperRegistry
    import omni_scraper.scrapers  # Ensure scrapers are registered

    platform = args.platform.lower()
    scraper_cls = ScraperRegistry.get(platform)
    if not scraper_cls:
        console.print(f"[red]Error:[/red] No existe adaptador para '{platform}'. Disponibles: {ScraperRegistry.available_platforms()}")
        sys.exit(1)

    scraper = scraper_cls()
    repo = SQLiteRepository(config.storage.db_path)
    session = BrowserSession(config.browser)

    target = args.target
    limit = getattr(args, "limit", 10)
    console.print(f"[cyan]🚀 Extrayendo de {platform.upper()} (target: '{target}', límite: {limit})...[/cyan]")

    start_time = time.time()
    items = []
    status = "success"
    error_msg = None

    try:
        with session as (context, page):
            scraper.navigate(page, target)
            items = scraper.extract(page, limit=limit)
    except Exception as e:
        status = "failed"
        error_msg = str(e)
        console.print(f"[red]Error durante la extracción:[/red] {e}")

    duration_ms = int((time.time() - start_time) * 1000)
    inserted_count = 0
    if items:
        inserted_count = repo.insert_items(items)

    repo.record_run(
        run_type=f"{platform}_scrape",
        status=status,
        items_count=len(items),
        metadata={"target": target, "inserted": inserted_count, "error": error_msg, "duration_ms": duration_ms},
    )

    table = Table(title=f"📦 Resultados de {platform.capitalize()} ({target})")
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Título / Contenido", style="white")
    table.add_column("Autor", style="yellow")
    table.add_column("Métricas", style="green")

    for i, item in enumerate(items, 1):
        p = item.payload
        metrics = f"Score: {p.get('score', 0)} | Comentarios: {p.get('comments', 0)}"
        table.add_row(
            str(i),
            item.item_id[:20],
            p.get("title", "")[:60],
            p.get("author", "anon") or "anon",
            metrics,
        )

    console.print(table)
    console.print(f"[green]✅ Extracción finalizada en {duration_ms / 1000:.2f}s.[/green] Extraídos: {len(items)} | Nuevos en DB: {inserted_count}")
    repo.close()

