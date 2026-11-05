#!/usr/bin/env python3
"""Compatibility entry point for the shared read-only progress report."""

import sys
from pathlib import Path

PROJECT_DIR = str(Path(__file__).resolve().parents[1])
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.progress_report import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
