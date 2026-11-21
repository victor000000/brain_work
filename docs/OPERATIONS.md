# Operations

The deployment owner keeps the authorized research window, pending work and receipts in a private handoff. One supervised explorer owns the live DuckDB file. While it runs, use logs for observation and the existing writer for plan requests. The supervisor and maintenance tools must agree on `BRAIN_LOG_DIR` so they share the same writer lock.

## Inspect a running service

```bash
make status
systemctl --user is-active brain-work-explorer.service
make progress
```

`make status` displays service status and the last line of the default `brain_logs/budget.log`. Its recipe tolerates an inactive unit and a missing log. Use `systemctl --user is-active` on the deployment host when the exit code matters. An unreachable user manager needs to be distinguished from an inactive service.

`make progress` reads the current and rotated logs for today in UTC. For a specific UTC date, set `REPORT_DAY` to a value in `YYYY-MM-DD` form and run `make progress DAY="$REPORT_DAY"`. Progress honors `BRAIN_LOG_DIR`. When the deployment overrides that directory, inspect its budget log there as well. Full health checks and database reports can open DuckDB. [Tools and side effects](../tools/README.md)

## Budget and platform limits

The shared state uses `BRAIN_BUDGET_STATE_PATH` or the default `.budget_state.json` under the log directory. A positive remaining-count observation with a valid provider reset interval expires at that deadline, including across a restart. After expiry the allowance is unknown until a new observation arrives. A newly observed count without a reset hint can still apply. An active exhaustion window takes precedence.

For a concurrent-slot refusal, let the existing runner observe its accepted parents and honor the provider's retry interval. For an exhausted daily window, retain the shared state and wait for reset evidence. The service normally waits and continues running. If authorization covers one window only, stop it before another window begins. Submission caps and unresolved correlation checks retain their own deferrals.

## Pause and preserve ownership

1. Pause new experiments and campaign automation. Record known pending parent handles, probe owners, submission requests and the last observations privately.
2. For an authorized stop, run `make stop`. The unit's `KillMode=control-group` covers the supervisor and its children. Check the user unit's state and that the writer has exited before opening the DB from another process. Consult the supervisor log if a child appears to respawn.
3. Keep the database and any adjacent WAL together in place. Preserve the existing private logs, ledgers, plan hashes, receipts and Parquet exports. Remote jobs may finish while local polling is stopped.
4. On the next authorized start the explorer opens DuckDB and executes `CHECKPOINT` before schema initialization. If recovery reports corruption, retain the DB/WAL pair and the error for the deployment owner. Repeating startup or deleting a WAL can lose the evidence needed for recovery. [Startup code](../simulate_alphas.py) · [Troubleshooting](TROUBLESHOOTING.md)

## Recover an interrupted run

Check the stored owner and the last confirmed event before choosing an action.

| Observed state | Recovery action |
|---|---|
| A simulation has a native parent receipt and is still running | Observe the same handle. Normal startup scans up to 64 qualifying `SUBMITTED` parents from the previous six hours, including partially fetched multi-sim batches. Compare the recovered handles with the private list. |
| A selected probe has an older parent receipt | With exclusive maintenance ownership, poll the existing probe as described below. Its exact-owner lookup also works outside the normal startup window. |
| A simulation submission may have reached the provider, but its receipt is missing or conflicts with the stored payload | Preserve the claim and escalate it for reconciliation. Leave new dispatch for that owner on hold. |
| An alpha submission is `PENDING` or `VERIFIED` in the request journal | Follow the existing request through the verification path. It observes native alpha or submission progress. A visible `dateSubmitted` confirms acceptance. A timeout or an expired progress endpoint leaves the outcome uncertain. |

The general explorer can generate fresh work and start background submission checks. If the pause exceeded six hours, the scan hit its 64-parent cap, or an expected owner is missing, reconcile the outstanding handles before enabling fresh dispatch. A status-reconciliation script for eligible alphas also opens the DB, authenticates and writes local status. Inspect its source when choosing a maintenance action. [Parent recovery](../runner/explore_loop/reattach.py) · [Submission verification](../runner/verify_submit.py) · [Alpha status reconciliation](../tools/reconcile_submissions.py)

## Validate a new alpha submission

The runner reads and checks `regular.code` before patching the description or starting a new submission. A missing expression, unreadable response or timeout records a deferral and returns `CHECK_UNAVAILABLE`. An expression that fails scope validation records a `SCOPE_COMPLIANCE` failure and returns `SCOPE_BLOCKED`.

A fresh attempt after an explicit HTTP 403 or 429 rejection checks the expression again. Pending and verified journal entries follow the existing GET-only reconciliation path. [Submission flow](../runner/submit/flow.py)

## Queue or inspect a selected probe

A frozen plan contains a nonempty `batches` list. Each batch supplies 1–10 expressions, settings and one template tag per expression. For an authorized running writer, set `PLAN_FILE` to the private plan path and publish its request from the deployment checkout.

```bash
.venv/bin/python -m tools.queue_probe_plan --plan "$PLAN_FILE" --request
```

This command hashes the plan and writes a request to the log directory's `probe_requests/` inbox. The writer validates it and records `APPLIED` with queue IDs or `REJECTED` with a reason. Native simulation acceptance requires a later parent receipt. Direct validation and `--apply` open DuckDB and require exclusive maintenance access. An explicit `--db` selects the database for those direct modes. [Plan CLI](../tools/queue_probe_plan.py)

For a stopped explorer, set `PROBE_ID` from the private record. The first command inspects that owner. The second is for an authorized poll of a previously recorded parent.

```bash
.venv/bin/python -m tools.submit_selected_probe --probe-id "$PROBE_ID"
.venv/bin/python -m tools.submit_selected_probe --probe-id "$PROBE_ID" --poll
```

Both commands take `explorer.lock`, open the deployment checkout's project DB and checkpoint it. Inspection prints private JSON and stays offline. Polling authenticates, verifies the parent and payload, then observes and stores one pass. Wait the reported `next_poll_after_seconds` interval before another pass. A terminal stored parent returns its existing state. Keep stdout, logs and receipt values private.

`--execute` is the separate dispatch mode for a newly authorized queued owner. Use recovery polling for an existing receipt. A parent marked `COMPLETE` still needs child-result analysis. [Selected-probe CLI](../tools/submit_selected_probe.py) · [Status and data definitions](DATA.md)
