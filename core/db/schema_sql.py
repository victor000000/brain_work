"""Raw DDL string for all simulation-related tables.

Kept as a single executescript-able string so init_tables can apply it in
one shot. Idempotent — every statement is `CREATE TABLE/INDEX IF NOT EXISTS`.

The text itself lives in two constants — `core/db/schema_core_sql` (simulation
records, results and platform checks) and `core/db/schema_priors_sql` (pyramid
targets, cell priors and submission bookkeeping) — concatenated here so this
stays the single import path callers and tests already use.
"""

from core.db.schema_core_sql import CORE_SCHEMA_SQL
from core.db.schema_priors_sql import PRIORS_SCHEMA_SQL

SCHEMA_SQL = CORE_SCHEMA_SQL + PRIORS_SCHEMA_SQL
