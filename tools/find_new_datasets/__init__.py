"""Find datasets exposed by BRAIN that are not yet in local brain_data.duckdb.

CLI: `python3 -m tools.find_new_datasets [--all-subcats]`
"""

from tools.find_new_datasets.runner import main

__all__ = ["main"]
