"""Thresholds and timestamp formats shared by the health check functions.

Split out of `tools/healthcheck/checks.py`, which re-exports them. The values
are calibrated to the pv/option scope the project actually runs in (see
`core.scope`), not to the pre-cleanup 62-category database.
"""

# In-scope pv/option database (2026-10-02 prune): ~196k field rows across
# 47 datasets. The pre-cleanup 100k/200 thresholds described a different DB.
MIN_FIELDS = 100_000
MIN_DATASETS = 20
MIN_REGIONS = 5

# Freshness windows.
ALPHA_RESULTS_MAX_AGE_DAYS = 7
FIELDS_MAX_AGE_DAYS = 14
EXPLORER_PROGRESS_MAX_AGE_HOURS = 24

FIELD_REFRESH_KEY = "last_pv_option_refresh"
_TS_FORMATS = ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S")
