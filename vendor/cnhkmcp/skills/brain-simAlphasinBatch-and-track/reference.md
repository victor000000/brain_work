# brain-simAlphasinBatch-and-track Reference

## Suggested Folder Layout
- `configs/`: 凭证配置与模板
- `data/`: alpha 输入 JSON
- `outputs/`: 状态 CSV 与汇总产物
- `scripts/`: 主代码与辅助脚本
- `scripts/batch_simulator.py`: 主入口
- `scripts/ace_lib.py`: BRAIN API 会话与通用能力

## Core Files
- `scripts/batch_simulator.py`: batch submission, concurrency, polling, CSV persistence, resume.
- `scripts/ace_lib.py`: BRAIN API session helper.
- `data/alpha_list.json`: 推荐输入路径（兼容 `alpha_list.json`）
- `outputs/simulation_status.csv`: 推荐输出路径

## Run Template
```powershell
Set-Location "untracked/skills/brain-simAlphasinBatch-and-track"
python scripts/batch_simulator.py --config configs/config.json --alpha-json data/alpha_list.json --output-csv outputs/simulation_status.csv --batch-size 3 --concurrency 2 --detached
```

## Long-Task Controls
- `--detached`: 后台启动并立即返回
- `--task-id`: 可选任务ID
- `--tasks-dir`: 任务根目录（默认 `outputs/tasks`）
- `--status <task_id>`: 查询后台任务状态并退出
- `--tail-lines N`: 查询时输出日志尾部行数

```powershell
python scripts/batch_simulator.py --status "<task_id>" --tail-lines 60
```

若继续使用旧路径，程序会自动 fallback：
- `alpha_list.json`
- `config.json`

## Resume Rules
Resume depends on:
1. Same output CSV file
2. Same alpha content/settings/type (same `fingerprint`)

## Typical CSV Fields
- `fingerprint`, `alpha_type`, `sim_id`, `status`, `alpha_id`
- `pnl`, `sharpe`, `turnover`, `fitness`
- `error`, `error_details`

## Timeout/Long-Run Handling
- Timeout does not automatically mean failure.
- Check CSV update and status distribution before concluding.
- Prefer rerun with same CSV for resume behavior.
