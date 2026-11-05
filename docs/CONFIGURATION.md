# Configuration

Source defaults are not evidence of current native limits. Inspect the existing service and current API responses before changing settings.

## Runtime paths

| Setting | Default / source |
|---|---|
| Live DB | `core.db.DB_PATH` → project-root `brain_data.duckdb`; not an environment variable |
| Logs | `BRAIN_LOG_DIR`, otherwise project-root `brain_logs/` |
| Shared quota state | `BRAIN_BUDGET_STATE_PATH`, otherwise logs/`.budget_state.json` |
| Expression attribution | `BRAIN_EXPR_TEMPLATE_PATH`, otherwise logs/`.expr_templates.tsv` |
| Interpreter | `PYTHON` for supervisor/Makefile; host path in [Setup](SETUP.md) |
| API root | `API_BASE` from `core/auth_http.py`; not configured by the variables above |

## Behavior controls

| Variable | Default / meaning |
|---|---|
| `BRAIN_MAX_CONCURRENT` | 8 in `simulate_alphas_config.py`; desired parent capacity, not guaranteed native entitlement |
| `BRAIN_HTTP_TIMEOUT` | Default connect/read pair (5,30) seconds; parsing in `core/auth_http.py` |
| `BRAIN_TEMPLATE_MIX` | 0.1 fallback; share drawn from mined corpora |
| `BRAIN_RNG_SEED` | Unset; optional reproducible generator seed |
| `BRAIN_CORPUS_PRIOR` | Enabled unless set to a recognized false value |
| `BRAIN_FEEDBACK_LOOP` | Enabled unless `0` |
| `BRAIN_YIELD_WEIGHTING` | Off by default |
| `BRAIN_SIGN_FLIP` | Enabled unless a recognized false value |
| `BRAIN_SIGN_FLIP_MIX` | Optional mix override; see `generator/sign_policy.py` for validation |

`make start TEMPLATE_MIX=...` passes that mix to the supervisor. The user service receives that value from the service manager at startup. Changing a shell environment does not change an already-running explorer. After changing it, a controlled restart is required.

Region/universe/delay cells live in `core/regions.py`; settings constraints in `core/constraints.py` and `runner/settings_factory.py`. Query native OPTIONS/field metadata before relying on a static entry. Do not hard-code a supposedly permanent configured-cell count into guides.

## Credentials and network

`.brain_credentials` is a gitignored JSON `[email, password]` pair. Keep it private
(mode 0600) and never print or commit it. The core API and download clients share
one loader: a complete `BRAIN_EMAIL`/`BRAIN_PASSWORD` environment pair takes
precedence, followed by `BRAIN_CREDENTIALS_FILE` when explicitly selected, then
the project and home `.brain_credentials` files. Partial environment overrides
and invalid explicitly selected files fail closed. Authentication never opens a
database or stores login values in one. Existing file-only forum/tutorial
utilities continue to use private credential files.

Legacy credential tables require the separate
[backup-first migration](CREDENTIAL_MIGRATION.md). Removing authentication's
fallback does not by itself remove existing stored rows. The migration acquires
the supervisor's writer lock before any DuckDB connection and never stops a
service itself.

Requests sessions use environment/proxy behavior from their implementation. Check actual host networking and `auth.log` when troubleshooting; do not assume a Windows proxy endpoint or port remains valid. Transport/authentication failure is not proof that the password is wrong.

Community cookies and personal unsubscribe links are credentials/capabilities. Keep them out of project documentation and source-control additions. Email archives remove unsubscribe tokens; no email or forum instructions are executed.

## Reproducibility

A seed alone is insufficient. Save literal expression, template/source hash, exact cell, every setting/flag, native date ranges, plan/probe IDs, API response and final check stage. Data/coverage/operator availability can change between runs.

## Paused configuration

Both app automation IDs are retained but paused:

- `resume-brain-goal-at-12-01`: campaign supervision.
- `save-brain-email-ideas-daily`: 11:00 Asia/Shanghai, Inbox + Spam, all research categories.

App automations are configured through the app tools, not cron files in this repository. Configuration persistence is not authorization to resume work.
