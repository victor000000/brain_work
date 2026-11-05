---
name: brain-deep-explore
description: >-
  Ralph-style daily quant research loop for BRAIN. Use when user asks for 持续自我探索、日内循环、
  每天一次目标诊断、small-step迭代、single/cross enhance决策、批量回测追踪、
  达到4个可提交Alpha后停止。 Strictly orchestrates only five skills:
  brain-nextMove-analysis, brain-makeSomeGem, brain-inspectRawTemplate-create-Setting,
  brain-enhance-template, brain-simAlphasinBatch-and-track.
allowed-tools:
  - Read
  - Grep
  - Glob
  - RunTerminal
  - ManageTodoList
user-invocable: true
---

# Brain Deep Explore (Ralph Daily Loop)

## Core Objective
Maintain one daily research loop with strict discipline:
1. Run goal diagnosis **once per NY day**.
2. Continue **small-step iterations** in the same day:
   generate / enhance / setting / batch-sim / review.
3. Stop only when **4 submit-ready Alphas** are verified by BRAIN MCP checks.

## Hard Constraints
- Only use these five capability skills in orchestration:
  - `brain-nextMove-analysis`
  - `brain-makeSomeGem`
  - `brain-inspectRawTemplate-create-Setting`
  - `brain-enhance-template`
  - `brain-simAlphasinBatch-and-track`
- Do not add extra strategy engines or external workflow branches.
- Reuse long-task rules: detached run, polling, artifact-first judgement, resume by stable artifacts.

## Artifact Flow Contract (Must Follow)
- `brain-nextMove-analysis`
   - output for downstream: daily objective/constraints (state fields)
   - next input: parameter target for `brain-makeSomeGem`
- `brain-makeSomeGem`
   - outputs:
      - idea file: `.../data/<dataset>_<region>_delay<delay>/*_idea_*.json`
      - expression file: `.../data/<dataset>_<region>_delay<delay>/final_expressions.json`
   - next input:
      - `brain-inspectRawTemplate-create-Setting` MUST consume `*_idea_*.json`
      - `final_expressions.json` is supplemental only
- `brain-inspectRawTemplate-create-Setting`
   - input: idea file only (`*_idea_*.json` naming required)
   - outputs: `settings_candidates.json`, `alpha_list.json`
   - next input: `alpha_list.json` -> `brain-simAlphasinBatch-and-track`
- `brain-enhance-template`
   - input: idea json(s)
   - outputs: `enhanced_templates_*.json`, `enhanced_final_expressions_*.json`
   - next input: inspect path requires idea-json form; expression-only output is not direct inspect input
- `brain-simAlphasinBatch-and-track`
   - input: `alpha_list.json`
   - output: `simulation_status.csv`
   - next input: evidence review + MCP submission-check

## Daily Loop Phases (Concrete)
1. **Daily Diagnose (once/day)**
   - Execute `brain-nextMove-analysis` once.
   -lafu Write daily objective and constraints into loop state.
2. **Generate Candidate Pool**
   - Based on diagnosis, run `brain-makeSomeGem` with target region/delay/universe.
   - Use `brain-makeSomeGem` to build broad candidates.
   - Capture BOTH outputs:
     - `*_idea_*.json` (template/idea/expression_list)
     - `final_expressions.json` (expression-only list)
3. **Expand Settings**
   - Use `brain-inspectRawTemplate-create-Setting` with `*_idea_*.json` as input to create multi-setting alpha list.
   - You can use multi-tasking to process multiple idea files, each idea should have its own output, do not mix all ideas together and do not miss of handleing any idea file.
   - Do NOT use `final_expressions.json` as direct input to inspect step.
4. **Batch Sim & Track**
   - Use `brain-simAlphasinBatch-and-track` with fixed CSV path for resume.
5. **Evidence Review**
   - Review sim status distribution and failure tags.
   - Decide next step: re-setting / single enhance / cross enhance / regenerate.
6. **Enhance (Evidence-gated)**
   - Single mode for local repair.
   - Cross mode for complementary template fusion with strict metadata consistency.
7. **MCP Submission Readiness Check**
   - Use `mcp_brain-api_get_submission_check` on candidate alpha IDs.
   - Count submit-ready alphas.
8. **Stop Gate**
   - Stop when submit-ready count >= 4.
   - Do not stop by iteration/no-progress unless safety flags are explicitly enabled.

## Decision Gate for Enhance Mode
- Prefer **single enhance** when:
  - only one promising template cluster exists;
  - metadata inconsistent across templates;
  - issue is local instability or parameter sensitivity.
- Prefer **cross enhance** when:
  - at least two complementary winners exist;
  - metadata is consistent (dataset/region/delay and required universe consistency);
  - objective is diversification with retained economic meaning.

## Iteration Discipline
- Each iteration modifies at most 1-2 variables.
- Keep iteration artifacts and verdict in persistent state file.
- If no progress for configured streak, fallback to regenerate path.
- Maintain a `loop_units` queue and execute one unit per iteration.
- In runner mode, mark unit pass only when output includes `<promise>COMPLETE</promise>`.

## State & Scripts
- State template: [templates/daily_state.template.json](templates/daily_state.template.json)
- State schema: [schemas/loop_state.schema.json](schemas/loop_state.schema.json)
- Helper script: `python scripts/ralph_daily_loop.py --help`
- Auto-pick latest makeSomeGem handoff files: `python scripts/ralph_daily_loop.py auto-pick-artifacts --state ...`
- Record artifact handoff: `python scripts/ralph_daily_loop.py set-artifacts --state ...`
- Validate artifact handoff: `python scripts/ralph_daily_loop.py validate-handoff --state ... --require-exists true`
- Outer runner: `python scripts/ralph_runner.py --help`
- Detailed execution rules: [reference.md](reference.md)
- Trigger and command examples: [examples.md](examples.md)

## Output Contract
Always report:
1. current day_key and whether diagnosis already executed
2. current iteration index and selected branch (generate/setting/sim/single/cross)
3. simulation status summary from CSV
4. submit-ready alpha count (checked via BRAIN MCP)
5. continue/stop decision with reason
6. artifact handoff used in this round:
   - makeSomeGem idea file path
   - makeSomeGem final expressions path
   - inspect input idea file path
   - batch sim input alpha_list path
