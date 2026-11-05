"""Per-region allowed neutralization values, from OPTIONS /simulations.

2026-05-01 snapshot. The data is split across two sub-modules — regions that
expose STATISTICAL vs. those that don't — so each definition fits comfortably
under the 100-line cap while still being readable. The merged
ALLOWED_NEUT_BY_REGION mapping below is exactly what callers used to import.
"""

from core.constraints._neut_no_statistical import NEUT_NO_STATISTICAL
from core.constraints._neut_with_statistical import NEUT_WITH_STATISTICAL

ALLOWED_NEUT_BY_REGION = {**NEUT_WITH_STATISTICAL, **NEUT_NO_STATISTICAL}
# Authenticated OPTIONS /simulations, 2026-10-23, now advertises this for IND.
# Evidence: brain_logs/python_alpha_schema_20261023.json. Refresh this cell
# for the source-matched Python study without inferring other account access.
ALLOWED_NEUT_BY_REGION["IND"] = ALLOWED_NEUT_BY_REGION["IND"] | {"STATISTICAL"}

# Legacy: regions where STATISTICAL neutralization is rejected.
# Derived from ALLOWED_NEUT_BY_REGION; kept for backward-compat with callers
# that still import this set.
NO_STATISTICAL_REGIONS = {r for r, allowed in ALLOWED_NEUT_BY_REGION.items() if "STATISTICAL" not in allowed}
