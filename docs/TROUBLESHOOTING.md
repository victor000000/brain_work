# Troubleshooting

Use actual process, receipt and native-response evidence. Do not restart or replay simply because an observer expired.

| Symptom | Check | Action / boundary |
|---|---|---|
| Project Python missing | `.venv/bin/python --version` | Create the checkout’s CPython 3.12 environment using [Setup](SETUP.md#install-validation-dependencies). |
| Service inactive or failed | `systemctl --user is-active brain-work-explorer.service`, then the user journal and supervisor log | Check manager availability and reconcile outstanding owners before an authorized start. |
| Environment broke after moving the checkout | `readlink -f .venv/bin/python` | Recreate the environment in the intended checkout. For a deployment, render the unit again from that path. |
| Native parser fails to build or load | `cargo --version`, `cc --version`, `.venv/bin/python -m tools.python_library` | Install the stable Rust toolchain, linker and matching Python shared library, then rerun `make rust-ci`. |
| Authentication fails | `auth.log`: missing credentials, rejection, transport or rate limit | Diagnose the actual branch; do not rotate credentials by guess |
| HTTP429 CONCURRENT | Native body and live account jobs | Let existing runner poll/back off; not daily exhaustion |
| Daily quota exhausted | Native remaining/reset plus persisted state | Wait for evidenced reset; never delete flags to bypass quota |
| Parent progress stalls | Existing parent handle, Retry-After and native state | Observe the same parent at the indicated interval. |
| Parent vanished from local queue | Stored parent receipt, request owner and timing | The startup scan covers up to 64 parents in six hours. Follow [recovery by state](OPERATIONS.md#recover-an-interrupted-run). |
| Simulation POST disconnected before receipt | Full logged payload/claim | UNKNOWN: preserve owner, do not replay |
| Submission expression unavailable | `CHECK_UNAVAILABLE` in the check log | Review the failed detail read and allow the normal deferral to elapse. The next attempt fetches the expression again. |
| Submission returned HTTP 201 and `dateSubmitted` is still absent | Existing alpha and submission journal | Keep the request pending and reconcile the same owner. |
| Empty correlation body / pending checks | Same GET/check handle | Computation may still be pending; not PASS or terminal FAIL |
| DuckDB lock error | Actual owner process | Stop competing access; no snapshot-copy workaround |
| WAL still present after stop | Main DB plus adjacent WAL | Preserve both; do not delete or copy only the DB |
| A report shows old results | Selected source, snapshot-fallback notice, timestamp | Old fallback is historical; do not report it as current |
| Unknown operator / unit error | Native operator scope and exact field semantics | Correct a demonstrated mismatch before spending quota |
| MATRIX city/country/cluster field | Native description and role | Numeric type does not justify ranking category codes |
| High IS/TEST but no submission | Full native final checks | Robustness, concentration, region/ladder or correlation can still fail |
| Higher accepted count but same Expert progress | Current-quarter pyramid attribution and published OS metrics | Same-key count does not add pyramids; do not claim score gains |

## Logs to inspect

`brain_logs/supervisor.log` records process exits/backoff; `simulate_stdout.log` is append-only application output. `submit.log` carries native HTTP receipts and uncertain payloads; `poll.log` parent/child progress; `alpha.log` attribution/metrics; `check.log` native checks; `auth.log` login diagnostics; `budget.log` quota observations; `errors.log` collects warnings/errors.

Daily rotation uses UTC dates. Check current timestamps and matching batch/parent IDs. Several logs contain older fixed incidents; a historical traceback is not a new failure.

## Known operational gaps

- There is no documented audited reconcile-only startup switch. Long-pause recovery must address old receipts before enabling normal POSTs.
- Some legacy report helpers automatically try the live DB and then historical backups. They do not meet current log-only observation policy by default.
- The cleanup tool still advertises backups in old help/docstrings. That does not override the explicit no-routine-backup policy.
- Full check JSON is retained for new writes, but old empty `extra` rows remain and latest-per-check replacement is not full event history.
- Field metadata can be vague, e.g. “Mapping data.” Preserve uncertainty; do not invent a numeric interpretation.
- Native stage/status and dateSubmitted must be verified separately from local labels.

## Scope and policy failures

Inspect the original expression, field descriptions and dependencies when judging scope. The semantic checker blocks recognized EPS, EBIT, EBT and assets tokens even under a PV prefix. Confirm unresolved fields, partition use and atom compliance against the underlying metadata. [Scope implementation](../core/scope.py)
