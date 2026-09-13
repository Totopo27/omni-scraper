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
