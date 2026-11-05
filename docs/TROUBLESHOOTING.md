# Troubleshooting

Use actual process, receipt and native-response evidence. Do not restart or replay simply because an observer expired.

| Symptom | Check | Action / boundary |
|---|---|---|
| Project Python missing | `.venv/bin/python --version` | Run `make setup-dev`; Docker is not required |
| Service inactive or failed | `make status`, supervisor log, `journalctl --user -u brain-work-explorer` | Check authorization and failure before starting |
| Old venv points under `/root` | `readlink ~/.venvs/brain_work/bin/python` | Use the new project `.venv`; do not reuse the old container environment |
| Authentication fails | `auth.log`: missing credentials, rejection, transport or rate limit | Diagnose the actual branch; do not rotate credentials by guess |
| HTTP429 CONCURRENT | Native body and live account jobs | Let existing runner poll/back off; not daily exhaustion |
| Daily quota exhausted | Native remaining/reset plus persisted state | Wait for evidenced reset; never delete flags to bypass quota |
| Job stalls at35% | Poll same parent, Retry-After, actual native state | A slow/poll-timeout job is not failed; do not duplicate POST |
| Parent vanished from local queue | Durable receipt and reattach age | Reconcile handle; startup scan is limited to 6 hours/64parents |
| Simulation POST disconnected before receipt | Full logged payload/claim | UNKNOWN: preserve owner, do not replay |
| Submission201 but no dateSubmitted | GET existing alpha and submission owner | Keep pending;201 alone is not verified alpha acceptance |
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
