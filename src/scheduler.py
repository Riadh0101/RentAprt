"""Continuous monitoring: a cycle every CYCLE_INTERVAL_MINUTES plus a daily digest.

Run with `python main.py monitor` or `python -m src.scheduler`.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .pipeline import Monitor

logger = logging.getLogger(__name__)


def start(monitor: Monitor, interval_minutes: int, digest_hour: int, on_report=None):
    """Run one cycle immediately, then block running cycles on an interval."""

    def cycle():
        try:
            report = monitor.run_cycle()
            if on_report:
                on_report(report)
        except Exception:
            logger.exception("Monitoring cycle crashed; the scheduler stays active for the next run")

    def digest():
        try:
            monitor.daily_digest(send=True)
        except Exception:
            logger.exception("Daily digest failed")

    scheduler = BlockingScheduler()
    scheduler.add_job(cycle, IntervalTrigger(minutes=interval_minutes), id="cycle",
                      max_instances=1, coalesce=True)
    scheduler.add_job(digest, CronTrigger(hour=digest_hour, minute=0), id="digest",
                      max_instances=1, coalesce=True)

    logger.info("Hermes monitor started: cycle every %d min, daily digest at %02d:00",
                interval_minutes, digest_hour)
    cycle()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Hermes monitor stopped.")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from main import main
    main(["monitor"])
