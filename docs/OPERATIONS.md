# Operations

## Authorization and current window

The explorer explicitly checkpoints immediately after opening its writer and
before schema initialization. This protects indexes restored from WAL against
the automatic-checkpoint failure reproduced on DuckDB1.5.6 (upstream
https://github.com/duckdb/duckdb/issues/26106). It prevents that tested transition;
it does not repair an index already inconsistent. Never delete a WAL to recover.
The October23 score-index repair and scratch reproduction are recorded in
`brain_logs/duckdb_invalidation_recovery_20261023.json` and
`brain_logs/duckdb_art_reproduction_20261023.json`.

Research work and the supervised campaign are authorized again from 2026-10-21 13:51 UTC; the daily email automation remains paused. [Current state](CURRENT_STATE.md) records the allowance window, the reattached receipts and the published plans. Each allowance window still needs its own authorization, and an observation timeout never authorizes a replay.

The supervisor and explorer normally run indefinitely. Budget exhaustion makes the loop wait for a reset; it does not terminate the service. A one-window authorization therefore needs an explicit stop before another allowance window.

## Ownership rules

- One supervised explorer, one process owning the live DuckDB. Multiple connections/threads inside that process are coordinated; another process must not open the live file while it runs, even read-only.
- Native HTTP 201 with a parent receipt establishes simulation acceptance. It does not establish alpha acceptance.
- A timeout observing a job is not a terminal job failure. Poll the same handle; never replay a simulation or submission because the observer timed out. Automatic slow-job handling only reports and retains the job, including past the old 60-minute threshold. It does not cancel native jobs to free slots. Explicit cancellation requires a separate decision.
- Uncertain POST outcomes retain ownership. Do not reset their claims or regenerate the same payload to evade ownership.
- No routine DB copies, new blacklists, subscription changes or quota-state deletion.

## Normal inspection during an authorized run

```bash
systemctl --user status brain-work-explorer.service --no-pager
tail -n 20 brain_logs/explore.log
tail -n 20 brain_logs/submit.log
tail -n 20 brain_logs/poll.log
make progress
```

`make progress` reads logs. `make status` is also log/service-only. Health checks, many reports and downloads can open the DB; they are not interchangeable with log-only inspection.

Logs and internal timestamps use UTC. Scheduling instructions may use Asia/Shanghai (UTC+8). Date-check append-only logs and rotated filenames before treating an old error as current.

## Budget and platform limits

`core/budget/` stores last native remaining/reset evidence in `brain_logs/.budget_state.json` by default. Native remaining values can arrive asynchronously; quote the observation time. A local flag or an expected noon reset is not proof of available allowance.

A CONCURRENT rejection is not daily exhaustion. Respect Retry-After and let the sole runner manage slots. Submission caps and unresolved correlation checks are separate constraints; retain deferred candidates. Never bypass quota or use POST polling to find a reset.

## Pause and save

1. Stop creating experiments and pause the goal/campaign automation.
2. Save current receipts, pending owners, raw native observations, quota evidence, plan hashes and a compact handoff.
3. Use `make stop`; verify the service is inactive and its children have exited.
4. Preserve the DB **and any adjacent WAL**, Parquet, probe request/receipt files and logs. Stop is not proof that the WAL was checkpointed away.
5. Native jobs may finish remotely while local polling is paused. Do not cancel them or claim terminal reconciliation merely because the local process stopped.

No automatic DB backup is part of this procedure.

## Resume after explicit authorization

Inspect the pause checkpoint and actual native owners before new POSTs. The automatic reattach scanner currently considers SUBMITTED parents younger than **six hours**, capped at 64; it does not recover every older receipt automatically.

For a short, authorized restart, record pending handles, test production changes, stop/start the host service and verify each prior handle was reattached or terminally reconciled.

For a long pause, **do not blindly start the normal supervisor**: startup can generate fresh work while older receipts fall outside the reattach scan. Reconcile old parents and submission owners with GET-only observations in a controlled maintenance context first. The current documented runtime has no audited reconcile-only startup switch; arranging that context is an explicit remaining operational task, not a reason to replay work or start a duplicate writer.

The October 21 authorization was one window. Resuming in a later window requires the user's scope/allowance decision.

## Controlled probe plans

A finite plan contains `batches`; each batch has `expressions` (1–10), full `settings`, and one `template_tags` entry per expression.

During an authorized run, publish through the existing writer:

```bash
.venv/bin/python tools/queue_probe_plan.py \
  --plan brain_logs/your_frozen_plan.json --request
```

This mode does not open DuckDB. The writer validates/queues it and produces an APPLIED or REJECTED receipt in `brain_logs/probe_requests/`. APPLIED is not native acceptance. Preserve the plan hash, source hashes, probe owner, batch index and native parent handle separately. Never edit a published plan in place.

For an authorized experiment limited to one batch, keep the explorer stopped.
After validating and queueing the plan with `queue_probe_plan.py --apply`, use
`tools/submit_selected_probe.py --probe-id <owner>` to inspect that owner.
Adding `--execute` dispatches only that exact owner through the existing
quota-aware transport and durable receipt handling. It cannot select another
probe or fall through to random generation. It holds the explorer lock, opens
the sole database connection and checkpoints before querying. Inspection does
not authenticate or send API requests, but does open/checkpoint the database.

The command writes JSON to stdout, console logs to stderr, and progress/errors
to the usual project log files. It exits after dispatch, not after the remote simulation finishes.
Preserve its returned parent handle. Run the same command with `--poll` instead
of `--execute` for one GET/store pass through the existing poll machinery.
It verifies the stored parent payload against the owner and reattaches that
exact receipt even after the general explorer's six-hour recovery window.
Respect the reported `next_poll_after_seconds` (at least25seconds) before the
next pass. A completed parent returns its stored status without repolling;
missing/mismatched receipts raise an error without resubmitting. A parent marked
COMPLETE still needs child-result analysis: completion does not mean success or
alpha acceptance. Do not start the general
explorer merely to poll this batch. An accepted or uncertain owner is not sent
again; an observation timeout does not authorize resetting it. This command
does not submit alphas for acceptance or launch a new allowance window on its own.

Direct validation/`--apply` modes open the DB and require exclusive maintenance ownership.

## Receipts and reporting

Use [Data](DATA.md) to distinguish local simulation state, native checks, submission intent and actual ACTIVE/dateSubmitted acceptance. The dated October 21 observers under `brain_logs/` are campaign-specific; inspect their hard-coded window before reuse. Logs may truncate expression display; the stored expression/raw native payload is the full source.

When a one-window campaign genuinely exhausts native quota, reconcile known receipted jobs, retain uncertainty and cap deferrals, save measured outputs, stop before another reset and disable the campaign follow-up. The current user pause takes precedence over completing that window.
