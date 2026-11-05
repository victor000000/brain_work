"""Logger setup for pyramid_status (own name, distinct file handler)."""

import logging
import sys

from tools.pyramid_status._config import LOG_PATH

# Use a distinct logger name so we don't share handlers with other tools.
log = logging.getLogger("pyramid_status")
log.setLevel(logging.DEBUG)

# Stdout handler — INFO+ for human-readable feed.
_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_console)

# File handler — DEBUG+ for the persistent log.
_file = logging.FileHandler(LOG_PATH, mode="a")
_file.setLevel(logging.DEBUG)
_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_file)

# Line-buffer stdout so live tailing is responsive when run via nohup.
sys.stdout.reconfigure(line_buffering=True)
