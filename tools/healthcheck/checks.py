"""Individual health check functions.

Every check reports on a property that *should* hold for a healthy system, and
returns False when it does not. Thresholds are calibrated to the pv/option
scope the project actually runs in (see `core.scope`), not to the pre-cleanup
62-category database.

The checks live in `thresholds`, `check_base`, `db_checks`, `activity_checks`
and `pipeline_checks`; they are re-exported here so `from tools.healthcheck
import checks` keeps resolving for `__main__` and the tests.
"""

from tools.healthcheck.activity_checks import (  # noqa: F401
    check_alpha_recency,
    check_explorer_progress,
    check_processes,
)
from tools.healthcheck.check_base import _count, _parse_iso, _parse_utc, check  # noqa: F401
from tools.healthcheck.db_checks import check_integrity, check_results, check_scope  # noqa: F401
from tools.healthcheck.pipeline_checks import (  # noqa: F401
    check_field_freshness,
    check_generator,
    check_templates,
)
from tools.healthcheck.thresholds import (  # noqa: F401
    ALPHA_RESULTS_MAX_AGE_DAYS,
    EXPLORER_PROGRESS_MAX_AGE_HOURS,
    FIELD_REFRESH_KEY,
    FIELDS_MAX_AGE_DAYS,
    MIN_DATASETS,
    MIN_FIELDS,
    MIN_REGIONS,
)


def check_database(conn):
    """Check the pv/option tables are populated."""
    print("[Database]")
    ok = True
    fields = _count(conn, "SELECT COUNT(*) FROM data_fields")
    ok &= check("Data fields loaded", fields > MIN_FIELDS, f"{fields:,} fields")
    datasets = _count(conn, "SELECT COUNT(DISTINCT id) FROM datasets")
    ok &= check("Datasets loaded", datasets > MIN_DATASETS, f"{datasets} datasets")
    regions = _count(conn, "SELECT COUNT(DISTINCT region) FROM data_fields")
    ok &= check("Regions loaded", regions >= MIN_REGIONS, f"{regions} regions")
    return ok
