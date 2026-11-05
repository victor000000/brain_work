# brain-makeSomeGem Reference

## Folder Layout

```text
brain-makeSomeGem/
├── SKILL.md
├── reference.md
└── scripts/
  ├── headless_runner/
  │   ├── run.py
  │   ├── config.json
  │   └── README.md
  └── trailSomeAlphas/
    ├── run_pipeline.py
    ├── README.md
    └── skills/
      ├── brain-data-feature-engineering/
      └── brain-feature-implementation/
```

## Functional Responsibility
- `scripts/headless_runner/run.py`
  - User-facing entrypoint for parameterized runs
  - Handles config, retries, and orchestration
- `scripts/trailSomeAlphas/run_pipeline.py`
  - Core prompt + fetch + implement + merge pipeline
- `scripts/trailSomeAlphas/skills/brain-feature-implementation/data/...`
  - Final expression artifacts and intermediate outputs

## Canonical Run Template

```bash
cd scripts/headless_runner
python run.py --config config.json --data-category analyst --region <REGION> --delay <DELAY> --dataset-id <DATASET_ID> --universe <UNIVERSE> --instrument-type EQUITY --data-type <VECTOR|MATRIX> --detached
```

## Long-Task Controls
- `--detached`: 后台启动并立即返回
- `--task-id`: 可选任务ID
- `--tasks-dir`: 任务根目录（默认 `../outputs/tasks`）
- `--status <task_id>`: 查询后台任务状态并退出
- `--tail-lines N`: 查询时输出日志尾部行数

状态查询示例：

```bash
cd scripts/headless_runner
python run.py --status <task_id> --tail-lines 60
```

## Artifact Paths
- Ideas markdown:
  - `scripts/trailSomeAlphas/skills/brain-data-feature-engineering/output_report/{region}_delay{delay}_{datasetID}_ideas.md`
- Final expressions:
  - `scripts/trailSomeAlphas/skills/brain-feature-implementation/data/{datasetID}_{region}_delay{delay}/final_expressions.json`

## Known Failure Modes
- `401 Incorrect authentication credentials`:
  - Credentials issue from config/env, not pipeline logic.
- Missing config fields:
  - `scripts/headless_runner/run.py` should fail fast and print missing keys.
- Empty/invalid expression output:
  - Check dataset/data_type match and operator filtering conditions.
