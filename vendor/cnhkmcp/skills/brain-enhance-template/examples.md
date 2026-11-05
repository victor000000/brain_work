# examples.md

## 触发语句示例

- "把这个 idea 做单模板增强，命令行跑。"
- "用两个模板做 cross 增强。"
- "有好几个模板看起来不错，交叉互相参考进行增强。"
- "enhanced_final_expressions 为空，帮我排查。"
- "重跑 single/cross 并给我产物路径。"

## Single 示例

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --idea-json "testingTemplate/fundamental72_GLB_1_idea_1769854621979784200.json" --data-type MATRIX --detached
```

预期：
- 生成 `enhanced_templates_*.json`
- 生成 `enhanced_final_expressions_*.json`

## Cross 示例

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --idea-json-list "testingTemplate/fundamental72_GLB_1_idea_1769854621979784200.json" "testingTemplate/fundamental72_GLB_1_idea_1769854622483457900.json" --cross-prompt-style balanced --data-type MATRIX --detached
```

## 保守重跑示例（占位符更稳）

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --idea-json-list "<idea1>" "<idea2>" --cross-prompt-style conservative --data-type MATRIX --detached
```

## Single 直接文字输入示例

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --template-text "rank(ts_delta(close,5))" --idea-text "短期价格动量" --dataset-id "fundamental72" --region "GLB" --delay 1 --data-type MATRIX --detached
```

建议把模板中的可变字段写成 `{}`：

```powershell
python scripts/run.py --config configs/config.json --template-text "rank(ts_mean({ret}, 20) / ts_stddev({ret}, 20))" --idea-text "用收益率稳定性刻画中短期趋势" --dataset-id "fundamental72" --region "GLB" --delay 1 --data-type MATRIX --detached
```

## Cross 直接文字输入示例

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --manual-templates-json "[{\"template\":\"rank(ts_delta(close,5))\",\"idea\":\"短期价格动量\"},{\"template\":\"rank(ts_mean(volume,20))\",\"idea\":\"量能稳健性\"}]" --dataset-id "fundamental72" --region "GLB" --delay 1 --cross-prompt-style balanced --data-type MATRIX --detached
```

## Cross 直接文字输入示例（PowerShell 更稳）

```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --template-text "rank(ts_delta(close,5))" --idea-text "短期价格动量" --template-text-2 "rank(ts_mean(volume,20))" --idea-text-2 "量能稳健性" --dataset-id "fundamental72" --region "GLB" --delay 1 --cross-prompt-style balanced --data-type MATRIX --detached
```

## 查看后台日志

```powershell
# 将 <task_id> 替换为启动命令返回的 task_id
Get-Content "outputs/tasks/<task_id>/stdout.log" -Wait
```

## 查询后台任务状态

```powershell
# 打印任务状态 + stdout/stderr 日志尾部
python scripts/run.py --status "<task_id>" --tail-lines 60
```
