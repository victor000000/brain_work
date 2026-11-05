---
name: brain-make-some-gem
description: >-
  Generate GEM-style alpha expressions using brain-makeSomeGem.
  Use when user asks to 产出/生成 Alpha、GEM、表达式、final_expressions with parameters like region, datasetID, delay, universe.
   This skill is architecture-aware and must use both internal layers under scripts/: headless_runner (entry) and trailSomeAlphas (pipeline core).
allowed-tools:
  - Read
  - Grep
  - Glob
  - RunTerminal
  - ManageTodoList
---

# Brain Make Some GEM

## Instructions

1. Parse user intent and extract parameters:
   - required: `region`, `datasetID`, `delay`, `universe`
   - optional: `instrument_type` (default `EQUITY`), `data_type` (default `MATRIX`, optional `VECTOR`)
2. Resolve skill root and verify architecture components both exist:
   - `scripts/headless_runner/run.py` (entry runner)
   - `scripts/trailSomeAlphas/run_pipeline.py` (pipeline core)
3. Run via `scripts/headless_runner/run.py` (preferred path):

   ```bash
   cd scripts/headless_runner
   python run.py --config config.json --data-category analyst --region <REGION> --delay <DELAY> --dataset-id <DATASET_ID> --universe <UNIVERSE> --instrument-type <INSTRUMENT_TYPE> --data-type <DATA_TYPE> --detached
   ```

   Status query:
   ```bash
   python run.py --status <TASK_ID> --tail-lines 60
   ```

   Windows-safe invocation (recommended):
   ```powershell
   Set-Location "D:/BRAINProject/cnhkmcp/cnhkmcp/untracked/skills/brain-makeSomeGem/scripts/headless_runner"
   C:/Python313/python.exe run.py --config config.json --data-category <CATEGORY> --region <REGION> --delay <DELAY> --dataset-id <DATASET_ID> --universe <UNIVERSE> --instrument-type <INSTRUMENT_TYPE> --data-type <DATA_TYPE> --detached
   C:/Python313/python.exe run.py --status <TASK_ID> --tail-lines 60
   ```

4. Long-task execution policy (critical):
   - In PowerShell, chain commands with `;` (never use `&&`).
   - For expected long runs, launch with `--detached` and poll with `--status`.
   - If a CLI timeout happens, **do not** immediately mark as failed; first check whether output artifacts were generated.
   - Use PowerShell-safe checks like `Test-Path` and `Get-ChildItem` (avoid bash-style `||` fallback chains).

   4.1 Shell compatibility rules (must follow):
   - On Windows, prefer PowerShell for all commands in this skill.
   - Do not mix Bash with Windows path style like `C:\...` for `cd`.
   - If you run from a different working directory, call `run.py` with absolute path.
   - Status check failures should fall back to artifact checks (`stdout.log`, `stderr.log`, `final_expressions.json`) before declaring task failure.

5. Post-timeout recovery checklist:
   - Check ideas report path under `scripts/trailSomeAlphas/skills/brain-data-feature-engineering/output_report/`.
   - Check final expressions path under `scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json`.
   - If final file exists and can be parsed, treat run as success and report expression count.
   - Only classify as failed when both process status and artifact checks confirm failure.

6. Validate artifacts in pipeline output directory:
   - ideas report under `scripts/trailSomeAlphas/skills/brain-data-feature-engineering/output_report/`
   - final expressions under `scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json`
7. Return compact result summary:
   - parameters used
   - final expression file path
   - expression count
   - data type used (`VECTOR`/`MATRIX`)

## Architecture (Must Know)

This skill directory includes both execution layers:

```text
brain-makeSomeGem/
└── scripts/
   ├── headless_runner/
   │   ├── run.py
   │   └── config.json
   └── trailSomeAlphas/
      ├── run_pipeline.py
      └── skills/...
```

- `scripts/headless_runner` is the command entry and runtime wrapper.
- `scripts/trailSomeAlphas` is the actual idea→expression pipeline engine.
- Do not bypass to deleted legacy enhancer paths.

For full structure and failure-mode details, see [reference.md](reference.md).
For trigger examples, see [examples.md](examples.md).

## Examples
- User: “用 EUR analyst45 delay1 TOP2500 产出 VECTOR GEM”
- User: “帮我在 USA analyst10 delay0 TOP3000 生成一些 alpha expressions”
- User: “跑一下 analyst4，region EUR，delay1，universe TOP2500，输出 final_expressions”

## Utility Scripts
- Primary: `scripts/headless_runner/run.py`
- Core pipeline: `scripts/trailSomeAlphas/run_pipeline.py`

Detached task artifacts (from `scripts/headless_runner`):
- `../outputs/tasks/<task_id>/meta.json`
- `../outputs/tasks/<task_id>/stdout.log`
- `../outputs/tasks/<task_id>/stderr.log`

Always prefer the primary runner unless user explicitly asks to debug pipeline internals.

## Guardrails
- If config required fields are missing, report missing keys and stop.
- If API auth fails (`401`), report credentials issue clearly.
- If command times out, run artifact checks before declaring failure.
- Prefer background run + polling for long pipeline execution.
- Do not claim success without verifying final file exists.
- Do not modify pipeline code unless user explicitly requests code changes.

## Output Contract
Always return:
1. Final expression file path
2. Number of generated expressions
3. Whether run used `VECTOR` or `MATRIX`
4. Next optional action: simulation/batch evaluation
