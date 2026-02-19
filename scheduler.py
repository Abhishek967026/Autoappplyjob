"""Scheduler — Runs the job application pipeline on an hourly interval."""

import time
import schedule
import yaml
from main import run_pipeline
from utils.logger import logger


def load_interval():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config.get("scheduler", {}).get("interval_hours", 1)


def main():
    interval = load_interval()
    logger.info(f"Scheduler started. Running pipeline every {interval} hour(s).")

    # Run immediately on start
    run_pipeline()

    # Schedule recurring runs
    schedule.every(interval).hours.do(run_pipeline)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
