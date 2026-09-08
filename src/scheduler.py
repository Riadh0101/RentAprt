import sys
import time
import logging
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from run_cycle import run_single_cycle
from src.config import CYCLE_INTERVAL_MINUTES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("HermesScheduler")

def start_continuous_monitoring():
    """Start persistent monitoring scheduler running every 20 minutes."""
    print("="*70)
    print(f"🕒 HERMES AUTONOMOUS SCHEDULER STARTED")
    print(f"🔁 دورة التكرار: كل {CYCLE_INTERVAL_MINUTES} دقيقة بشكل دائم ومستقل")
    print(f"🚀 تشغيل الدورة الابتدائية الأولى فوراً...")
    print("="*70)

    cycle_count = 0

    def job_wrapper():
        nonlocal cycle_count
        try:
            run_single_cycle(cycle_count)
            cycle_count += 1
        except Exception as e:
            logger.error(f"Error encountered during monitoring cycle: {e}", exc_info=True)
            logger.info("Cycle error handled gracefully. Scheduler remains active for next tick.")

    # Execute cycle #1 immediately
    job_wrapper()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        job_wrapper,
        trigger=IntervalTrigger(minutes=CYCLE_INTERVAL_MINUTES),
        id="hermes_rental_cycle",
        name="Hermes 20-minute rental scan",
        replace_existing=True
    )

    try:
        logger.info(f"Scheduler active. Next cycle scheduled in {CYCLE_INTERVAL_MINUTES} minutes.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Hermes Scheduler stopped by user.")

if __name__ == "__main__":
    start_continuous_monitoring()
