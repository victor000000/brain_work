# Examples

## Trigger Phrases
- “帮我批量回测这个 alpha_list.json，并保存进 simulation_status.csv”
- “继续上次中断的 batch simulation（断点续传）”
- “把并发降到 1 重跑失败项”
- “统计 simulation_status.csv 里 COMPLETE/ERROR 数量”

## Expected Behavior
- Uses `scripts/batch_simulator.py` in this directory.
- 优先使用 `configs/config.json`，缺省时使用 env credentials (`BRAIN_EMAIL`, `BRAIN_PASSWORD`)。
- Summarizes result from CSV, not only from terminal tail.

## Recommended Command Pattern
- `python scripts/batch_simulator.py --config configs/config.json --alpha-json data/alpha_list.json --output-csv outputs/simulation_status.csv --batch-size 3 --concurrency 2 --detached`
- `python scripts/batch_simulator.py --status "<task_id>" --tail-lines 60`
