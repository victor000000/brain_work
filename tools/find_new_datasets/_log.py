"""Logger for find_new_datasets."""

import logging
import sys

from tools.find_new_datasets._config import LOG_PATH

# Use the shared "dl" logger name to merge with the download module's stream.
log = logging.getLogger("dl")
log.setLevel(logging.DEBUG)

_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_console)

_file = logging.FileHandler(LOG_PATH, mode="a")
_file.setLevel(logging.DEBUG)
_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s"))
log.addHandler(_file)

sys.stdout.reconfigure(line_buffering=True)
