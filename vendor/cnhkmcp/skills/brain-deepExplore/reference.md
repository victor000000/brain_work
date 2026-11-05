# brain-deepExplore Reference

## 1) Mission Lock
This workflow never changes its mission:
- one diagnosis per NY day
- continuous small-step intra-day loop
- stop only when 4 submit-ready alphas are validated by BRAIN MCP checks

## 1.1) Ralph Outer Loop Runner
- Use `scripts/ralph_runner.py` as optional outer loop executor.
- It executes one loop unit per iteration and checks completion token `<promise>COMPLETE</promise>`.
- It updates `loop_units[].passes` and writes runtime traces to `progress_log`.

## 2) Five-Skill Only Orchestration
The loop may only route actions to:
1. `brain-nextMove-analysis` (daily objective)
2. `brain-makeSomeGem` (candidate generation)
3. `brain-inspectRawTemplate-create-Setting` (raw template setting expansion)
4. `brain-enhance-template` (single/cross enhancement)
5. `brain-simAlphasinBatch-and-track` (batch simulation + resume)

No additional research branch is allowed.

## 2.1) Artifact Contract (Critical)

### brain-nextMove-analysis
- Output for next step: daily objective + constraints written into state.
- Next input consumer: `brain-makeSomeGem` parameter choices.

### brain-makeSomeGem
- Main outputs:
	- idea files: `.../data/<dataset>_<region>_delay<delay>/*_idea_*.json`
	- final expressions: `.../data/<dataset>_<region>_delay<delay>/final_expressions.json`
- Next input consumers:
	- `brain-inspectRawTemplate-create-Setting` MUST consume `*_idea_*.json`
	- `final_expressions.json` is supplemental for later merge/sanity checks, not inspect input.

### brain-inspectRawTemplate-create-Setting
- Required input: one idea json in the expected naming format (`<dataset>_<region>_<delay>_idea_<ts>.json`).
- Outputs:
	- `settings_candidates.json`
	- `alpha_list.json` (appendable)
- Next input consumer: `brain-simAlphasinBatch-and-track` uses `alpha_list.json`.

### brain-enhance-template
- Input: idea json(s) (`--idea-json` or `--idea-json-list`).
- Outputs: `enhanced_templates_*.json`, `enhanced_final_expressions_*.json`.
- Next input consumer:
	- If re-enter inspect flow, feed compatible idea json artifacts.
	- Expression-only outputs may be supplemental but are not inspect raw input.

### brain-simAlphasinBatch-and-track
- Required input: `alpha_list.json`.
- Outputs: `simulation_status.csv` (resume source of truth).
- Next input consumer: evidence review + MCP submission gate.

## 3) Step-by-Step Concrete Plan

### Step 0. Initialize Day State
- Build/load state file using NY date key.
- Ensure same day resumes existing state.
- Ensure output CSV path is stable for resume semantics.
- Seed loop units (`generate,setting,sim,review`) and keep one unit per iteration.

### Step 1. Daily Diagnose (Exactly Once)
- If `daily_diagnose.done` is false: run `brain-nextMove-analysis`.
- Save objective, constraints, preferred pyramid/competition target.
- Mark `daily_diagnose.done=true` and timestamp.
- If already true, skip and continue loop.

### Step 2. Candidate Generation
- Run `brain-makeSomeGem` with target region/delay/universe from Step 1.
- Capture BOTH `*_idea_*.json` and `final_expressions.json` paths.

### Step 3. Raw Template Setting Expansion
- Input MUST be one `*_idea_*.json` from Step 2 output.
- Run `brain-inspectRawTemplate-create-Setting` Part 1 to obtain candidates.
- Select one or more settings combinations based on objective.
- Append generated alphas into one stable `alpha_list.json` for the day.

### Step 4. Batch Simulation & Resume
- Run `brain-simAlphasinBatch-and-track` in detached mode.
- Poll status.
- On timeout: artifact-first checks before failure decision.
- Keep same CSV path across retries to preserve fingerprint resume.

### Step 5. Evidence Review
- Parse status summary: complete / failed / running.
- Tag failure mode: parameter mismatch, overfit pattern, invalid expression, sparse coverage.
- Update no-progress streak if key metrics fail to improve.

### Step 6. Enhance Decision Gate
Choose branch by evidence only:
- **single enhance**: local repair of one promising template.
- **cross enhance**: fuse two+ complementary templates with metadata consistency checks.
- **no enhance**: if issue is setting-only, return to Step 3.

### Step 7. Submission Readiness Gate (MCP)
- For top candidate alpha IDs, run `mcp_brain-api_get_submission_check` one by one.
- Count submit-ready alphas (pass criterion: submission check returns no blocking failure).
- Store count and checked alpha list in state.

### Step 8. Stop / Continue
- Stop when `submit_ready_count >= 4`.
- Else continue next iteration with minimal change set (max 1-2 variable changes).
- Default `check-stop` behavior should evaluate submit-ready target only.
- Enable safety stop explicitly when needed: `--enforce-max-iterations` and `--enforce-no-progress`.

## 4) Enhance Mode Safety Rules
- Cross mode requires strict metadata consistency among inputs.
- If consistency check fails, fallback to single mode.
- Conservative style first when recent rounds show instability.

## 5) Long-Task & Reliability Protocol
- Always prefer detached + polling for long steps.
- Timeout is not immediate failure.
- Artifacts are source of truth, then process status.
- Resume by stable artifact path (especially simulation status CSV).

## 6) State File Fields (Minimum)
- `day_key` (NY date)
- `daily_diagnose` object (`done`, `objective`, `constraints`, `done_at`)
- `iteration` object (`current`, `max`, `no_progress_streak`, `max_no_progress`)
- `artifacts` object (`gem_expression_file`, `alpha_list_file`, `sim_status_csv`, `enhance_outputs`)
- `submit_gate` object (`submit_ready_count`, `alpha_ids_checked`, `checked_at`, `verified_by_mcp`)
- `stop` object (`should_stop`, `reason`)
- `loop_units` list (`id`, `title`, `branch`, `passes`, `notes`)
- `progress_log` path (append-only run log)

## 7) Recommended Defaults
- `max_iterations_per_day = 12`
- `max_no_progress_streak = 3`
- `sim_poll_seconds = 90`
- `enhance_cross_default_style = balanced`

## 8) Failure Handling Matrix
- Auth/credential failure: hard stop, require config fix.
- No artifact + process dead: fail current step and record reason.
- Artifact exists but process timeout: treat as pending-success; continue verification.
- Cross consistency failure: fallback single mode.

## 9) End-of-Day Carryover
Persist unresolved queue to next day but do not carry `daily_diagnose.done=true` across day_key.

## 10) Completion Promise Rule
- A loop unit is treated as completed in runner mode only when command output contains `<promise>COMPLETE</promise>`.
- Missing promise means unit stays incomplete with failure notes for next iteration diagnosis.

## 11) Continuous Runner Behavior
- `ralph_runner.py` supports auto-refill when unit queue is empty.
- Suggested continuous config: large `--max-iterations`, `--ready-target 4`, `--auto-refill-units true`.
