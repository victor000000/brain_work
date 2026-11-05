# Data and storage

## Storage contract

`brain_data.duckdb` is the live application database. There is no supported SQLite backend or SQLite migration entry point. Some compatibility APIs and old comments retain SQLite-shaped terminology; the connection implementation is DuckDB.

Preserve the adjacent `brain_data.duckdb.wal` whenever present. At the October 21 pause the DB and WAL were both present; the container's exit is not proof that all committed WAL contents were checkpointed into the main file. Never delete the WAL as a temporary file.

While the explorer runs, no competing process may open the live file, even read-only. Use logs/exports or native GET-only observers. With the service stopped, any deliberate DB maintenance still needs an approved project-Python execution context and exclusive ownership. This documentation task did not open the DB.

Keep live DuckDB and Parquet. Routine backup copies and database images are not part of the workflow.

## Table map

Schemas are authoritative in `core/db/schema_core_sql.py`, `schema_priors_sql.py`, schema/init migration modules, `download/db_schema.py`, and dynamically ensured tracking tables.

| Table/group | Main purpose |
|---|---|
| `data_fields`, `datasets`, `dataset_categories` | Native metadata, descriptions, type, exact cell and coverage |
| `download_log`, `metadata` | Download progress and metadata bookkeeping |
| `simulations` | Parent/child ID, batch index, expression, raw settings, status, error and timestamps |
| `alpha_results` | Full expression, native result JSON, IS/TRAIN/TEST metrics, settings and status; migrations add attribution columns |
| `submission_checks` | Latest check set keyed by alpha/check name |
| `alpha_check_summary` | Counts and last check time |
| `check_failures` | Durable first/last failure, latest limit/value and repeat count |
| `submission_requests` | Pending/rejected/verified submission ownership, committed before POST |
| `submission_outcomes` | Template/cell/neutralization outcome aggregates |
| `polish_candidates` | Existing refinement claims and attempts |
| `probe_batches` | Frozen experiment payloads and pending/claimed/submitted/uncertain state |
| `pyramid_targets` | Region/delay/category counts, quarter bounds, gaps and score |
| Pyramid count/multiplier tables | Dated native pyramid observations |
| Cell priors / yield posterior | Research selection feedback, not verified OS results |
| Attribution/signature tables | Operators, fields, templates, signatures and diversity tracking |

Do not infer that a base CREATE TABLE string lists all columns in a migrated live DB.

## What is retained

The result writer stores the full expression and raw native alpha response, plus template attribution and settings. Native simulation errors retain their expression, settings, job ID and message where supplied. An opaque native FAIL without a message must remain opaque.

New `submission_checks.extra` writes preserve the full native check JSON, including dates, ratios and structured values. The existing alpha/check-name key and latest-set replacement semantics remain: this is not an append-only history of every poll. Historical empty extras were not backfilled. `check_failures` is durable failure aggregation, not a complete historical check-event stream.

Text logs often shorten expressions and round metrics. Never use those displays as an exact payload audit. Local `SUBMITTED` counts are bookkeeping; native ACTIVE/dateSubmitted is the acceptance authority.

## Parquet and JSON artifacts

| Artifact | Coverage / limitation |
|---|---|
| `brain_logs/campaign_20261021_measurements.json/.parquet` | Log-derived measured results; attribution included, display expressions/metrics have log limits |
| `campaign_20261021_measurement_summary.json` | Counts, completeness checks and native enrichment coverage |
| `*_native_audit.json` | Full captured native parent/child/alpha bodies and identity/settings checks |
| `*_results.json/.parquet` | Scoped analytical rows tied to raw source SHA |
| `*_analysis.json` | Measured conclusion, failed checks, next decision and limitations |
| Field catalog exports | Descriptions/availability; not actual historical market observations |
| Provider deliveries | Actual timestamped raw data and calculated values; separate acquisition contract |

Read exported Parquet independently of the live DB. In-memory DuckDB for artifact conversion does not open the live file. Verify row counts, IDs, expression identity, source hashes and schema on readback.

DuckDB parameter binding in nested COPY/source statements was ambiguous in a one-off exporter; use a separate source materialization followed by a single target-parameter COPY, or a validated exporter. That artifact error did not replay any BRAIN request.

## Exporting a catalog

The exporter requires exclusive, consistent input access. With an approved maintenance context and no writer:

```bash
.venv/bin/python -m tools.export_brain_catalog \
  --db brain_data.duckdb --output exports/brain_catalog_run_id
```

The output includes Parquet, JSONL/CSV, a compact metadata-only catalog DuckDB and checksums; it is a data product, not a full live-DB backup. It refuses an existing output destination. Do not start the paused explorer just to obtain this context.

Legacy report helpers may try the live file and then announce a historical backup fallback. The current policy is not to create backups to satisfy those helpers. Do not invoke their defaults while a writer owns the live file; stale fallback output is not current account evidence.

## Timestamps and delivery semantics

Logs use UTC. Stored strings may include UTC suffixes or offsets; `core/time_sql.py` supplies normalization for reports. A calendar-day report is different from an allowance window starting04:00UTC.

Metadata is keyed by actual dataset/field and region/universe/delay. Preserve units, NaN semantics, publication/availability timestamps and lookback dependencies. The provider contract covers US/mainlandChina PV/options values, not HongKong; see [the current handoff](data_requirements/CURRENT_BRAIN_PV_OPTIONS_REQUIREMENTS.md).
