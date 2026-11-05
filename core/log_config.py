"""Log file configuration — maps logger names to filenames.

Logs live in the project's own `brain_logs/` directory (gitignored): the
project writes nothing outside its tree. Set `BRAIN_LOG_DIR` to move them.
Auto-rotated daily at midnight; old logs get a date suffix:
submit.log -> submit.log.2026-04-04

Import LOG_DIR from here rather than resolving a path locally — one definition
means the test sandbox and the explorer cannot drift apart.
"""

import logging
import os
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.environ.get("BRAIN_LOG_DIR") or os.path.join(PROJECT_DIR, "brain_logs")

# Timestamps in UTC, project-wide. Every DB write already formats with
# time.gmtime (and a literal " UTC"), and log rotation is utc=True — but
# logging's default converter is localtime, so ad-hoc formatters (the tools'
# _log modules, download/, core/log.py before 2026-10-03) stamped the box's
# local zone (Asia/Shanghai, UTC+8), disagreeing with every DB row by 8 hours.
# The class attribute is read at format time, so setting it here covers every
# formatter created anywhere in the process — and this module is the single
# import every logging setup in the project already goes through.
logging.Formatter.converter = time.gmtime

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILES = {
    "simulate": "simulate.log",
    "submit": "submit.log",
    "poll": "poll.log",
    "check": "check.log",
    "errors": "errors.log",
    "generator": "generator.log",
    "alpha": "alpha.log",
    "auth": "auth.log",
    "budget": "budget.log",
    "slots": "slots.log",
    "runner": "runner.log",
    "ops": "ops.log",
    "group": "group.log",
    "settings": "settings.log",
    "db": "db.log",
    "diversity": "diversity.log",
    "fields": "fields.log",
    "explore": "explore.log",
    "download": "download.log",
}
