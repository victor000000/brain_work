---
name: brain-sim-alphas-batch-track
description: >-
  Batch submit and track WorldQuant BRAIN alpha simulations from JSON inputs with CSV-based resume.
  Use when user asks to 批量回测/批量提交 alpha、断点续传、查看 simulation_status.csv、重跑失败项、调并发(batch-size/concurrency).
allowed-tools:
  - Read
  - Grep
  - Glob
  - RunTerminal
  - ManageTodoList
---

# Brain Sim Alphas Batch Track

## Instructions
1. Confirm input files:
  - default alpha input: `data/alpha_list.json`（兼容根目录 `alpha_list.json`）
  - status output: user provided CSV (default `outputs/simulation_status.csv`)
2. Ensure credentials are provided:
  - preferred: `configs/config.json`
  - fallback: environment variables `BRAIN_EMAIL` / `BRAIN_PASSWORD`
3. Run from this skill directory using `scripts/batch_simulator.py`（独立技能，不依赖 makeSomeGem）.
4. This is a long-running task: use background execution + periodic polling by default.
5. Never treat a single terminal timeout as final failure.
6. After run/timeout, always verify status CSV exists and summarize rows by `status`.

## PowerShell Execution Rules
- Use `;` to chain commands (never use `&&`).
- Prefer PowerShell-safe checks: `Test-Path`, `Get-ChildItem`, `Import-Csv`.

## Standard Command
```powershell
Set-Location "untracked/skills/brain-simAlphasinBatch-and-track"
python scripts/batch_simulator.py --config configs/config.json --alpha-json data/alpha_list.json --output-csv outputs/simulation_status.csv --batch-size 3 --concurrency 2 --detached

# 查询后台任务状态（替换 task_id）
python scripts/batch_simulator.py --status "<task_id>" --tail-lines 60
```

## Long-Task Execution Protocol (Required)
1. Pre-check inputs before launch:
  - `configs/config.json` exists (or env credentials are present)
  - `data/alpha_list.json` exists
2. Prefer non-blocking execution for large runs:
  - Run task in background mode (`--detached`).
  - Poll progress every 60-180 seconds.
3. Progress source of truth is output CSV (`outputs/simulation_status.csv`), not terminal tail.
4. Timeout policy:
  - If command tracking times out, do **not** declare failure immediately.
  - First check whether CSV file exists, file size changed, or row count increased.
  - If artifacts are still updating, continue polling.
5. Failure declaration policy:
  - Only declare run failure when both conditions hold:
    - process appears stopped or unreachable, and
    - CSV has no progress for a sustained idle window (recommended: >= 3 minutes).

## Long-Task Result Checkpoints
- Minimum checks after each polling cycle:
  - CSV exists
  - total row count
  - `status` distribution (`COMPLETE/COMPLETED`, `ERROR/FAIL`, others)
- Final summary must include:
  - CSV path
  - total rows
  - counts by status
  - recommended next action (resume / rerun failed-only / lower concurrency)

## Resume Semantics (Must Respect)
- Resume key is `fingerprint` + same output CSV file.
- Do not claim “no resume” before checking:
  - same CSV path used
  - alpha content/settings/type unchanged

## Output Contract
Always return:
1. status CSV path
2. total rows and counts by `status`
3. submitted/skipped/completed/failed summary if available
4. next action recommendation (e.g., lower concurrency or rerun failed only)

## Guardrails
- Do not hardcode credentials in code or docs.
- If timeout occurs, check whether CSV has been updated before declaring failure.
- Do not change fingerprint logic unless explicitly asked.

For file map and field details, see [reference.md](reference.md).
For trigger examples, see [examples.md](examples.md).
