"""Runs the backup job on a recurring interval using the `schedule` library."""
import time
import schedule

from .logger import get_logger

logger = get_logger("scheduler")


def run_scheduled(manager, interval_minutes: int = 60):
    def job():
        logger.info("Scheduled backup starting...")
        manager.run_backup()
        logger.info("Scheduled backup finished.")

    job()  # run once immediately
    schedule.every(interval_minutes).minutes.do(job)
    logger.info("Scheduler active: running every %d minute(s). Press Ctrl+C to stop.", interval_minutes)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
