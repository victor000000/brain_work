# brain-makeSomeGem 无 UI 独立运行说明

这个目录用于**不经过 Web UI**，直接运行“直接来点Alpha”对应的流水线。

## 目录结构

- `run.py`：无 UI 入口
- `config.json`：必填运行配置（账号和大模型信息）
- `../trailSomeAlphas/`：已复制的核心流水线代码

## 1) 先填写 config.json（必填）

`config.json` 需要以下字段（缺失会直接报错并提示补齐）：

- `brain_email`
- `brain_password`
- `moonshot_base_url`
- `moonshot_model`
- `moonshot_api_key`

## 2) 必要环境变量（可选）

在 PowerShell 中设置（示例）：

```powershell
$env:BRAIN_EMAIL="your_email@example.com"
$env:BRAIN_PASSWORD="YOUR_CREDENTIAL"
$env:MOONSHOT_API_KEY="YOUR_CREDENTIAL"
```

说明：
- 如果 `config.json` 已正确填写，通常不需要再设置这些环境变量

## 3) 运行

```powershell
Set-Location "d:\BRAINProject\cnhkmcp\cnhkmcp\untracked\skills\brain-makeSomeGem\headless_runner"
C:/Python313/python.exe run.py --config config.json --data-category analyst --region EUR --delay 1 --dataset-id analyst4 --universe TOP2500 --instrument-type EQUITY --data-type VECTOR
```

常用可选参数：

```powershell
--ideas-file <path_to_ideas.md>
--regen-ideas
--max-fields 50
--max-operators 300
--no-operators-in-prompt
--moonshot-base-url <url>
--moonshot-retries 3
--moonshot-retry-backoff 2
```

先做参数检查（不执行）：

```powershell
C:/Python313/python.exe run.py --config config.json --data-category analyst --region EUR --delay 1 --dataset-id analyst4 --universe TOP2500 --instrument-type EQUITY --data-type VECTOR --dry-run
```

## 4) 结果输出

核心产物在：

- `../trailSomeAlphas/skills/brain-feature-implementation/data/<dataset>_<region>_delay<delay>/final_expressions.json`

## 5) 与 UI 流程关系

`run.py` 本质上是调用：

- `../trailSomeAlphas/run_pipeline.py`

与 UI 点击“直接来点Alpha”后触发的后端主流程一致，只是改为纯命令行。
