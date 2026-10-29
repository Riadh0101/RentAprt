#!/usr/bin/env python3
"""Hermes rental monitor — command-line entry point."""
import argparse
import logging
import subprocess
import sys
from typing import List, Optional

from src.config import load_settings
from src.dashboard import render_cycle, render_dashboard
from src.database import Database
from src.notifier import EmailNotifier, TelegramNotifier, preview
from src.pipeline import Monitor, read_watchlist
from src.scraper import EmlakjetClient, FetchError


def _configure_console(level: str):
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError):
                pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _check(settings, db: Database) -> int:
    """Validate configuration and connectivity without changing any data."""
    print(f"Database:        {settings.db_path} (ok)")
    print(f"Budget:          {settings.max_budget_tl:,.0f} TL (hard limit {settings.exceptional_budget_limit_tl:,.0f} TL)")
    print(f"Rooms allowed:   {', '.join(settings.allowed_rooms)}")
    print(f"Interval:        every {settings.cycle_interval_minutes} min, digest at {settings.daily_digest_hour:02d}:00")
    print(f"Watchlist:       {len(read_watchlist(settings))} URL(s)")
    print(f"Telegram:        {'configured' if settings.telegram_enabled else 'NOT configured (alerts print to console)'}")
    print(f"Email:           {'configured → ' + settings.alert_recipient_email if EmailNotifier(settings).enabled else 'NOT configured'}")
    label, url = settings.feed_urls()[0]
    with EmlakjetClient(settings) as client:
        try:
            items = client.fetch_feed(url, label)
            print(f"Emlakjet:        reachable — {len(items)} listings in '{label}' feed")
        except FetchError as e:
            print(f"Emlakjet:        FAILED — {e}")
            return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes autonomous rental monitor (Istanbul Aydın University)")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run-once", help="Run a single search cycle and show the dashboard")
    run_p.add_argument("--notify", action="store_true",
                       help="Kept for compatibility; undelivered alerts are always sent")
    mon_p = sub.add_parser("monitor", help="Run continuously on an interval")
    mon_p.add_argument("--interval", type=int, help="Minutes between cycles")
    dash_p = sub.add_parser("dashboard", help="Show statistics and top listings")
    dash_p.add_argument("--min-score", type=int, default=0)
    dash_p.add_argument("--limit", type=int, default=15)
    sum_p = sub.add_parser("summary", help="Print the daily digest")
    sum_p.add_argument("--send", action="store_true", help="Also send it via Telegram/email")
    sub.add_parser("check", help="Validate configuration and connectivity")
    sub.add_parser("test", help="Run the automated test suite")
    args = parser.parse_args(argv)

    settings = load_settings()
    _configure_console(settings.log_level)
    command = args.command or "run-once"

    if command == "test":
        return subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"])

    db = Database(settings.db_path)
    if command == "check":
        return _check(settings, db)
    if command == "dashboard":
        print(render_dashboard(db, args.min_score, args.limit))
        return 0

    with EmlakjetClient(settings) as client:
        monitor = Monitor(settings, db, client, TelegramNotifier(settings), EmailNotifier(settings))
        if command == "summary":
            text = monitor.daily_digest(send=args.send)
            print(preview(text))
        elif command == "monitor":
            from src.scheduler import start
            start(monitor, args.interval or settings.cycle_interval_minutes, settings.daily_digest_hour,
                  on_report=lambda r: print(render_cycle(r)))
        else:
            report = monitor.run_cycle()
            print(render_cycle(report))
            print(render_dashboard(db, min_score=settings.score_daily_digest, limit=10))
    return 0


if __name__ == "__main__":
    sys.exit(main())
