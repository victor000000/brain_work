"""Logging setup — console + daily-rotated per-module log files.

Logs rotate at midnight. Old logs get date suffix:
  brain_logs/submit.log -> brain_logs/submit.log.2026-04-04
"""

import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler

from core.log_config import LOG_DIR, LOG_FILES

_FMT_INFO = logging.Formatter("%(asctime)s %(message)s")
_FMT_DEBUG = logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s")

# Timestamps in UTC, matching every DB write in the project (all formatted with
# time.gmtime and a literal " UTC") and the handlers' own utc=True midnight
# rotation. Before this, log lines carried the box's local zone (Asia/Shanghai,
# UTC+8), so a log line and the DB row it described disagreed by 8 hours.
_FMT_INFO.converter = time.gmtime
_FMT_DEBUG.converter = time.gmtime


def _make_daily_handler(path, level=logging.DEBUG):
    """Create a TimedRotatingFileHandler that rotates at midnight."""
    handler = TimedRotatingFileHandler(
        path,
        when="midnight",
        backupCount=30,
        utc=True,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    handler.setFormatter(_FMT_DEBUG)
    return handler


def setup_logging(*, console_stream=None):
    """Configure the 'brain' logger with console + daily-rotated files."""
    log = logging.getLogger("brain")
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG)

    # Console: INFO
    ch = logging.StreamHandler(sys.stdout if console_stream is None else console_stream)
    ch.setLevel(logging.INFO)
    ch.setFormatter(_FMT_INFO)
    log.addHandler(ch)

    # Main simulate log: all DEBUG, daily rotation
    log.addHandler(_make_daily_handler(os.path.join(LOG_DIR, "simulate.log")))

    # Errors only: WARNING+, daily rotation
    log.addHandler(
        _make_daily_handler(
            os.path.join(LOG_DIR, "errors.log"),
            level=logging.WARNING,
        )
    )

    return log


def get_file_logger(name):
    """Get a dedicated file logger with daily rotation."""
    logger = logging.getLogger(f"brain.{name}")
    if logger.handlers:
        return logger

    filename = LOG_FILES.get(name, f"{name}.log")
    path = os.path.join(LOG_DIR, filename)
    logger.addHandler(_make_daily_handler(path))
    return logger
