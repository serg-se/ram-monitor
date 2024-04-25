import logging
import logging.handlers
import os
import sched
import sys
import time

import psutil
import requests

USAGE_THRESHOLD = int(os.environ.get("USAGE_THRESHOLD") or 50)  # In percents
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL") or 5)  # In seconds
API_URL = os.environ.get("API_URL") or "https://1.1.1.1"

logger = logging.getLogger(__name__)


def bytes_to_gb(bytes_size: int) -> str:
    return "{:.2f} GB".format(bytes_size / (1024**3))


def get_ram_info() -> [int, float]:
    """Return a total RAM in bytes and used RAM in percents."""
    ram = psutil.virtual_memory()

    total_ram = ram.total
    percent_used = ram.percent
    return total_ram, percent_used


def check_ram() -> None:
    """Check current RAM usage and raise an alarm if it exceeds the threshold."""
    total_ram, percent_used = get_ram_info()
    total_ram_gb = bytes_to_gb(total_ram)

    if percent_used > USAGE_THRESHOLD:
        message = f"RAM usage exceeded {USAGE_THRESHOLD}% of {total_ram_gb}: {percent_used}%!"
        logger.critical(message)
        send_alert(message)
    else:
        logger.info(f"RAM usage: {percent_used}% of {total_ram_gb}")


def send_alert(message: str) -> None:
    """Notify API about excessive RAM usage."""
    try:
        payload = {"message": message}
        response = requests.post(API_URL, data=payload)
        if response.status_code == 200:
            logger.info("Alarm was sent successfully!")
        else:
            logger.error(f"Error sending alarm: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending alarm: {e}")


def set_up_logging() -> None:
    """Set up logging configuration to log to file and print to stdout."""
    if not os.path.exists("logs"):
        os.mkdir("logs")

    # Add file rotating handler
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/ram_usage.log", maxBytes=10240, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s " "[in %(pathname)s:%(lineno)d]")
    )
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # Add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s ")
    )
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    logger.setLevel(logging.INFO)
    logger.info("Monitoring startup")


def daemon(local_handler: sched.scheduler) -> None:
    """Check RAM usage by interval."""
    local_handler.enter(CHECK_INTERVAL, 1, daemon, (local_handler,))
    check_ram()


def set_up_scheduler() -> None:
    """Start monitoring daemon."""
    handler = sched.scheduler(time.time, time.sleep)
    handler.enter(0, 1, daemon, (handler,))
    handler.run()


if __name__ == "__main__":
    set_up_logging()
    set_up_scheduler()
