#!/usr/bin/env python3
import sys
import argparse
import logging
from src.config import config
from src.db.database import Database
from src.scheduler.runner import SchedulerRunner
from src.dashboard.app import DashboardApp

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("hermes-rental-monitor")

def main():
    parser = argparse.ArgumentParser(description="Hermes Autonomous Rental Monitoring System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: run-once
    subparsers.add_parser("run-once", help="Run a single search and update cycle")

    # Command: monitor
    monitor_parser = subparsers.add_parser("monitor", help="Start continuous monitoring loop")
    monitor_parser.add_argument("--interval", type=int, default=config.CYCLE_INTERVAL_MINUTES, help="Interval in minutes")

    # Command: dashboard
    subparsers.add_parser("dashboard", help="Show live statistics and top listings table")

    # Command: summary
    subparsers.add_parser("summary", help="Generate and print daily market digest")

    # Command: test
    subparsers.add_parser("test", help="Execute end-to-end self-test of all modules")

    args = parser.parse_args()

    # Initialize Database
    db = Database(config.DB_PATH)
    runner = SchedulerRunner(db)

    if args.command == "run-once" or args.command is None:
        logger.info("Executing single monitoring cycle...")
        result = runner.run_cycle()
        print("\nCycle Result Summary:", result["summary"])
        # Display updated dashboard
        DashboardApp(db).render()

    elif args.command == "monitor":
        runner.start_monitoring_loop(interval_minutes=args.interval)

    elif args.command == "dashboard":
        DashboardApp(db).render()

    elif args.command == "summary":
        digest = runner.generate_daily_digest()
        print("\n" + digest)

    elif args.command == "test":
        print("\n[TEST] 1. Testing Database initialization...")
        assert db.get_connection() is not None
        print(" -> DB initialized successfully.")

        print("[TEST] 2. Testing Search Cycle & Normalization...")
        res = runner.run_cycle()
        assert res["listings_found"] > 0
        print(f" -> Found {res['listings_found']} listings, inserted/updated properly.")

        print("[TEST] 3. Testing Deduplication & Scoring...")
        active = db.get_all_active()
        assert len(active) > 0
        for p in active:
            assert 0 <= p.score <= 100
        print(f" -> {len(active)} active properties scored properly.")

        print("[TEST] 4. Testing Dashboard...")
        DashboardApp(db).render()
        print("\nALL SYSTEM TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
