# brain-makeSomeGem Examples

## Trigger Examples

1. “帮我用 EUR / analyst45 / delay1 / TOP2500 生成 VECTOR GEM alpha”
2. “Run analyst10 in USA delay0 TOP3000 and give me final_expressions”
3. “用 analyst4 + EUR + D1 + TOP2500 产出一些表达式”

## Expected Behavior

- The skill should use `scripts/headless_runner/run.py` as entry.
- Long runs should use `--detached`, then poll with `--status`.
- It should verify output under:
  - `scripts/trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json`
- It should report expression count and output path.

## Recommended Command Pattern

```bash
cd scripts/headless_runner
python run.py --config config.json --data-category analyst --region <REGION> --delay <DELAY> --dataset-id <DATASET_ID> --universe <UNIVERSE> --instrument-type EQUITY --data-type <VECTOR|MATRIX> --detached
python run.py --status <task_id> --tail-lines 60
```

## Error Handling Examples

- Missing config fields:
  - Return missing key names from `scripts/headless_runner/config.json` validation.
- Auth issue (`401`):
  - Return that credential/authentication failed, without changing pipeline code.
