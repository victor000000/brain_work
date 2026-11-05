# Operational tools

Use [Operations](../docs/OPERATIONS.md) for authorization/ownership, [Data](../docs/DATA.md) for sources, and [Development](../docs/DEVELOPMENT.md) for checks. Research resumed on October 23; consult the handoff for current scope.

Commands below use project Python in an authorized runtime/maintenance context. Do not start the explorer to obtain that context during a pause. A “read-only” DB tool still cannot compete with the live writer.

## Select a tool by effect

| Purpose | Entry point | Effect / requirement |
|---|---|---|
| Log-only daily progress | `make progress`, `tools/progress_from_log.py` | Reads logs; safe alongside an authorized runner |
| Stored result counts | `tools/progress_report.py`, `tools/check_progress.py` | Opens DB/report source; local status is not verified acceptance |
| Detailed reads | `tools/reads.py` | DB source required |
| Full health | `tools/healthcheck/`, `make health` | Includes DB/API checks; inspect before use |
| Frozen probe request | `tools/queue_probe_plan.py --plan FILE --request` | File publication only; existing writer validates and submits |
| Direct probe validation/apply | Same CLI without `--request` / with `--apply` | Opens DB; requires exclusive maintenance ownership |
| Catalog export | `python -m tools.export_brain_catalog --db INPUT --output DIR` | DB read, new metadata export, Parquet readback verification |
| Template sweep | `tools/registry_sweep.py`, `make sweep` | Renders and validates; DB source required, no claim of native acceptance |
| Template report | `tools/template_report.py` | DB/report source required |
| Metadata refresh | `tools/refresh_pv_option_fields.py --resume` | API GETs plus DB writes; not alongside writer |
| Community harvesting | `tools/spider_forum.py --comments` | Network and source-file writes; read-only remote harvesting |
| Learn/help content | `tools/harvest_learn_docs.py`, `harvest_help_center.py` | Network/source-file writes |
| Settings discovery | `tools/discover_simulation_matrix/` | Native OPTIONS discovery; inspect CLI |
| Apply discovered matrix | `tools/apply_discovery_and_redownload/` | Configuration/DB mutation, not a status command |
| Dataset discovery | `tools/find_new_datasets/` | Native/local comparisons; inspect storage effects |
| Mine source templates | `mine_forum_templates.py`, `mine_help_center_templates.py`, `parse_cnhkmcp_templates.py` | Writes derived corpora; extraction is not validation |
| Mine result shapes | `tools/mine_proven_floor.py` | Reads evidence and writes corpus; floor is not acceptance |
| Explain a shape | `tools/explain_template.py` | Reads rationale/source links |
| Check/submit alphas | Root `check_alphas.py`, `check_alphas_retry.py` | Can submit; never run as an observer or competing DB owner |
| Reconcile submissions | Root `reconcile_submissions.py` | Read source first for network/DB effects; preserve existing owners |
| Pyramid refresh/backfill | `tools/refresh_pyramid_targets/`, `refresh_pyramid_state.py`, backfill tools | DB writes; quarter context matters |
| Portfolio analysis | `tools/portfolio_kpi/` | DB source required; not native published combined score |
| Cleanup | `tools/cleanup_db.py` | Destructive execute mode; legacy help mentions backups, current policy does not authorize routine copies |
| Blacklist update | `make blacklist-update` | Not part of authorized workflow; do not run |

## Source selection

Legacy shared `open_report_db` tries the live DB then announces historical backup fallback. An explicit input uses that source. Do not invoke the default while the explorer owns the file, and do not create backups to make reports run. Prefer existing exports for observation.

DB-writing downloads, repairs, backfills and cleanup require the writer stopped and an approved maintenance context. A tool being listed here does not authorize its mutation.

## Campaign-specific tools

The dated `brain_logs/*20261021.py` observers/exporters/reconciliation helpers are gitignored work artifacts. Several hard-code the October 21 allowance window. Inspect them before reuse; do not generalize their scope to another day or full history.

The account capture requires credential-file auth to avoid DB fallback. Fixed-plan audits validate plan/source hashes and exact native identities/settings. Once a study is closed and result artifacts reference an audit SHA, do not overwrite that raw snapshot gratuitously.

## Email archive

The Gmail routine is an app automation using connector read/search tools; it is not a cron job in this directory. The local renderer lives at `docs/forum/brain_email_ideas_20261021/rebuild_index.py`. See [Email research](../docs/EMAIL_RESEARCH.md) for scope, pause and artifact contracts.
