"""Main CLI entry point for Omni-Scraper."""

import argparse
import sys

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from omni_scraper.config import load_config
from omni_scraper.cli.commands import handle_clean, handle_db, handle_doctor


def apply_cli_overrides(config, args):
    """Apply command line arguments onto the configuration instance."""
    if getattr(args, "headless", False):
        config.browser.headless = True
    if getattr(args, "cdp_url", None):
        config.browser.cdp_url = args.cdp_url
    if getattr(args, "browser", None):
        config.browser.browser_type = args.browser
    if getattr(args, "executable_path", None):
        config.browser.executable_path = args.executable_path
    return config


def build_parser() -> argparse.ArgumentParser:
    """Construct the command line interface parser."""
    parser = argparse.ArgumentParser(
        prog="omni-scraper",
        description="Omni-Scraper: Modular, anti-detection stealth scraping harness.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--browser",
        choices=["brave", "chrome", "edge", "chromium"],
        default=None,
        help="Browser type to use (default: brave)",
    )
    parser.add_argument(
        "--executable-path",
        default=None,
        help="Explicit path to browser executable",
    )
    parser.add_argument(
        "--cdp-url",
        default=None,
        help="Connect to an external Chromium / Fortress instance over CDP (e.g. 'http://localhost:9222')",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Doctor command
    subparsers.add_parser("doctor", help="Run pre-flight health diagnostics")

    # 2. Database command
    db_parser = subparsers.add_parser("db", help="Manage SQLite storage and retention")
    db_sub = db_parser.add_subparsers(dest="db_action", required=True)
    db_sub.add_parser("stats", help="Show database volume, unique items, and platforms")
    purge_parser = db_sub.add_parser("purge", help="Purge items older than N days")
    purge_parser.add_argument("--days", type=int, default=30, help="Days of retention (default: 30)")
    purge_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # 3. Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean transient cache files")
    clean_parser.add_argument("--dry-run", action="store_true", help="Simulate cleanup without deleting")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    if args.command == "doctor":
        handle_doctor(config, args)
    elif args.command == "db":
        handle_db(config, args)
    elif args.command == "clean":
        handle_clean(config, args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
