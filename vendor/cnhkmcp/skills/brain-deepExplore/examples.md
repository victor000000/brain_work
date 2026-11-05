# brain-deepExplore Examples

## Trigger Examples
- “用 Ralph loop 开始今天的量化研究，今天只做一次目标诊断，然后持续迭代直到4个可提交Alpha。”
- “继续今天的 deepExplore 循环，不要重复 nextMove。”
- “检查是否已经达到4个可提交Alpha，没到就继续小步循环。”

## Typical Day Start
```powershell
Set-Location "untracked/skills/brain-deepExplore"
python scripts/ralph_daily_loop.py bootstrap --state outputs/loop_state.json --max-iterations 12 --max-no-progress 3
python scripts/ralph_daily_loop.py mark-nextmove --state outputs/loop_state.json --objective "<today objective>" --constraints "<competition/pyramid constraints>"
python scripts/ralph_daily_loop.py seed-units --state outputs/loop_state.json --units "generate,setting,sim,review"
python scripts/ralph_daily_loop.py new-iteration --state outputs/loop_state.json --branch generate
```

## Correct Handoff: makeSomeGem -> inspectRawTemplate
```powershell
# 1) pick latest idea file produced by makeSomeGem
$idea = Get-ChildItem "../brain-makeSomeGem/scripts/trailSomeAlphas/skills/brain-feature-implementation/data/analyst45_EUR_delay1/*_idea_*.json" |
	Sort-Object LastWriteTime -Descending |
	Select-Object -First 1 -ExpandProperty FullName

# 2) inspect step MUST use idea file as input
Set-Location "../brain-inspectRawTemplate-create-Setting"
python scripts/process_template.py --file "$idea"
```

Note:
- `final_expressions.json` is expression-only and should not be used as direct input to `process_template.py`.

## Ralph Outer Runner
```powershell
python scripts/ralph_runner.py --state outputs/loop_state.json --agent-command "echo ^<promise^>COMPLETE^</promise^> unit={unit_id} branch={branch}" --max-iterations 200 --ready-target 4 --auto-refill-units true --unit-sequence "generate,setting,sim,review"
```

## Decide Enhance Mode
```powershell
# metadata consistent + complementary winners => cross
python scripts/ralph_daily_loop.py decide-enhance --state outputs/loop_state.json --metadata-consistent true --complementary true --instability false

# otherwise single
python scripts/ralph_daily_loop.py decide-enhance --state outputs/loop_state.json --metadata-consistent false --complementary false --instability true
```

## Update Simulation Summary
```powershell
python scripts/ralph_daily_loop.py update-sim --state outputs/loop_state.json --sim-csv "../brain-simAlphasinBatch-and-track/outputs/simulation_status.csv" --complete 8 --failed 3 --running 2 --progressed true
```

## MCP Submission Gate Update
```powershell
# After using BRAIN MCP submission-check capabilities on candidate alpha IDs:
python scripts/ralph_daily_loop.py update-submit-gate --state outputs/loop_state.json --ready-count 3 --verified-by-mcp true --alpha-ids "a1,a2,a3"
python scripts/ralph_daily_loop.py check-stop --state outputs/loop_state.json --ready-target 4
```

## MCP Result File Driven Submission Gate
```powershell
python scripts/ralph_daily_loop.py update-submit-from-checks --state outputs/loop_state.json --checks-json "outputs/submission_checks.json"
python scripts/ralph_daily_loop.py check-stop --state outputs/loop_state.json --ready-target 4
```

## Record & Validate Artifact Handoff
```powershell
python scripts/ralph_daily_loop.py auto-pick-artifacts --state outputs/loop_state.json --set-default-downstream true

python scripts/ralph_daily_loop.py set-artifacts --state outputs/loop_state.json \
	--gem-idea-file "../brain-makeSomeGem/scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/<dataset>_<region>_<delay>_idea_<ts>.json" \
	--gem-expression-file "../brain-makeSomeGem/scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json" \
	--inspect-input-idea-file "../brain-makeSomeGem/scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/<dataset>_<region>_<delay>_idea_<ts>.json" \
	--alpha-list-file "../brain-inspectRawTemplate-create-Setting/processed_templates/<idea_stem>/alpha_list.json" \
	--sim-status-csv "../brain-simAlphasinBatch-and-track/outputs/simulation_status.csv"

python scripts/ralph_daily_loop.py validate-handoff --state outputs/loop_state.json --require-exists true
```

## When Reaching Goal
```powershell
python scripts/ralph_daily_loop.py update-submit-gate --state outputs/loop_state.json --ready-count 4 --verified-by-mcp true --alpha-ids "a1,a2,a3,a4"
python scripts/ralph_daily_loop.py check-stop --state outputs/loop_state.json --ready-target 4
python scripts/ralph_daily_loop.py summary --state outputs/loop_state.json
```
