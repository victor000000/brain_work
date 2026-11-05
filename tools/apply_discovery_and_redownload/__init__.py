"""Apply universe-discovery results to REGION_CONFIG, clear stale download_log
entries, then re-run the field download as a fresh subprocess.

CLI: `python3 -m tools.apply_discovery_and_redownload`
"""

from tools.apply_discovery_and_redownload.runner import main

__all__ = ["main"]
