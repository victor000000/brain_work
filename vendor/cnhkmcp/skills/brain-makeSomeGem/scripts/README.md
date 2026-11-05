# brain-makeSomeGem scripts 总入口说明（给 AI）

本目录包含两层：

- `headless_runner/`：对外入口（应直接运行）
- `trailSomeAlphas/`：底层流水线实现（不应直接运行）

## 关键规则

1. **默认只跑 `headless_runner/run.py`**。
2. **不要直接执行 `trailSomeAlphas/run_pipeline.py`**，除非用户明确要求调试底层 pipeline。
3. 所有常规 GEM 生成任务（用户给 region/datasetID/delay/universe）都走 `run.py`。

## 标准执行方式

```powershell
Set-Location "scripts/headless_runner"
python run.py --config config.json --data-category analyst --region <REGION> --delay <DELAY> --dataset-id <DATASET_ID> --universe <UNIVERSE> --instrument-type EQUITY --data-type <VECTOR|MATRIX> --detached
python run.py --status <task_id> --tail-lines 60
```

## 为什么不能直接跑 run_pipeline.py

- `run.py` 负责统一入口参数、配置校验、重试与兼容处理。
- `run_pipeline.py` 是底层执行引擎，直接跑会绕过上层约束与保护逻辑。

## 产物路径

- 结果文件：
  - `trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json`
- ideas 报告：
  - `trailSomeAlphas/skills/brain-data-feature-engineering/output_report/<region>_delay<delay>_<dataset>.md`

## 参考文档

- 入口说明：`headless_runner/README.md`
- 底层流水线说明：`trailSomeAlphas/README.md`
