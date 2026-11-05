"""Fetch the OPTIONS /simulations schema from BRAIN."""

import sys

from tools.discover_simulation_matrix._config import API_BASE
from tools.discover_simulation_matrix._log import log


def fetch_schema(session):
    resp = session.options(f"{API_BASE}/simulations", timeout=30)
    if resp.status_code != 200:
        log.error("OPTIONS /simulations -> HTTP %d", resp.status_code)
        sys.exit(1)
    return resp.json()
