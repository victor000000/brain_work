---
name: brain-enhance-template
description: >-
  Headless template enhancement skill for trailSomeAlphas-compatible flow.
  Use when user asks for 模板增强、cross增强、多模板融合增强、无UI命令行运行、
  产物检查、single/cross重跑、enhanced_final_expressions排障.
allowed-tools:
  - Read
  - Grep
  - Glob
  - RunTerminal
  - ManageTodoList
---

# Brain Enhance Template

## Hard Rules
- For direct text input, every `template` must include at least one `{}` datafield placeholder (example: `{ret}`).
- If a `template` has no `{...}` placeholder, stop immediately and return validation error.

## Instructions
1. Always run from this skill root and use single entrypoint: `scripts/run.py`.
2. Verify config before execution: `configs/config.json`.
3. Single mode accepts file input (`--idea-json`) or direct text input (`--template-text` + metadata args).
4. Cross mode accepts file input (`--idea-json-list`) or direct text input (`--manual-templates-json` or `--template-text` + `--template-text-2`) with shared metadata args.
5. Text input mode requires `--dataset-id`, `--region`, and `--delay` to build valid idea filenames.
6. Template text guidance (align frontend prompt): use `{}` for replaceable datafields, e.g. `{ret}`.
7. Text input constraints (align frontend prompt):
  - `dataset-id` should contain both letters and digits (e.g. `fundamental28`)
  - `region` should be a valid region token such as `GLB/USA/CHN`
  - `delay` should be integer in range `[0, 10]`
  - cross manual mode requires at least 2 template groups
8. Cross mode hard requirement: all input ideas must share the same `region`, `universe`, and `dataset`/`dataset_id`.
9. If cross inputs violate metadata consistency, fail fast and stop before enhancement.
10. For long-running execution, use detached mode (`--detached`) by default.
11. Treat runs as long tasks: timeout is not immediate failure—check artifacts first.
12. Report outcome with: command, output files, expression count, and next action.

## Long Task Protocol (Required)
1. Start with a run identifier (`task_id`) and print a concise launch record:
  - command
  - start time
  - mode (`single` or `cross`)
2. Keep streaming mode on and monitor in intervals (recommended 5-15s checks).
3. Track task state conceptually as:
  - `starting` → `running` → `completed` / `failed` / `cancelled`
  - include progress hints from logs when available.
4. During long silent periods, do not fail immediately. First perform artifact-first checks in the idea directory.
5. If idle timeout is reached, classify by evidence:
  - `completed`: final artifact exists and contains non-empty expressions.
  - `failed`: process exits with error and no usable artifact.
  - `running/unknown`: no new logs yet but process still alive; continue monitoring or ask whether to cancel.
6. Prioritize these artifacts for status and result judgement:
  - `enhanced_templates_*.json`
  - `enhanced_final_expressions_*.json`
7. Recovery rule: on transient failures (network/API/rate-limit), retry once with the same inputs before declaring hard failure.
8. Read runtime logs from `outputs/tasks/<task_id>/stdout.log` and `stderr.log`.
9. Final report must include:
  - task_id
  - final state
  - key output files
  - expression count in `enhanced_final_expressions_*.json`
  - next suggested action (rerun / adjust prompt style / inspect validator).

## Standard Commands

### Single mode
```powershell
# Run from brain-enhance-template root
python scripts/run.py --config configs/config.json --idea-json "<idea_json_path>" --data-type MATRIX --detached
```

### Cross mode
```powershell
# Run from brain-enhance-template root
python scripts/run.py --config configs/config.json --idea-json-list "<idea1.json>" "<idea2.json>" --cross-prompt-style balanced --data-type MATRIX --detached
```

### Single mode (direct text input)
```powershell
# Run from brain-enhance-template root
python scripts/run.py --config configs/config.json --template-text "<template_text>" --idea-text "<idea_text_optional>" --dataset-id "fundamental72" --region "GLB" --delay 1 --data-type MATRIX --detached
```

### Cross mode (direct text input)
```powershell
# Run from brain-enhance-template root
python scripts/run.py --config configs/config.json --manual-templates-json "[{\"template\":\"<t1>\",\"idea\":\"<i1>\"},{\"template\":\"<t2>\",\"idea\":\"<i2>\"}]" --dataset-id "fundamental72" --region "GLB" --delay 1 --cross-prompt-style balanced --data-type MATRIX --detached
```

## Progressive Docs
- Detailed options and troubleshooting: [reference.md](reference.md)
- Trigger examples and expected outputs: [examples.md](examples.md)

## Guardrails
- Never hardcode credentials.
- Do not call `scripts/enhance_template.py` directly unless debugging internals.
- In cross mode, never mix templates from different `region`, `universe`, or `dataset`/`dataset_id`.
- Keep `FEATURE_IMPLEMENTATION_DIR` consistent with dataset/region/delay metadata.
- Prefer local dependency folder `brain-feature-implementation/` under this skill.
