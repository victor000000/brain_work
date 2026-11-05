"""Platform constraints derived from OPTIONS /simulations.

Refresh by running `python3 -m tools.discover_simulation_matrix` and mirroring
the per-region neutralization map. Encoding constraints prevents 400 errors
at simulation submit time.

Public API kept stable for `from core.constraints import ALLOWED_NEUT_BY_REGION, ...`
"""

from core.constraints.neutralization import (
    ALLOWED_NEUT_BY_REGION,
    NO_STATISTICAL_REGIONS,
)
from core.constraints.position import MAX_TRADE_POSITION_CONFLICT, NO_MAX_POSITION_REGIONS

__all__ = [
    "ALLOWED_NEUT_BY_REGION",
    "MAX_TRADE_POSITION_CONFLICT",
    "NO_MAX_POSITION_REGIONS",
    "NO_STATISTICAL_REGIONS",
]
