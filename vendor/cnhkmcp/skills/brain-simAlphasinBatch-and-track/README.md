# brain-simAlphasinBatch-and-track 使用说明

这个目录用于批量提交 WorldQuant BRAIN alpha simulation，并支持基于 CSV 的断点续传。

这是一个独立技能目录，与 `makeSomeGem` 无耦合依赖。

## 建议目录结构

- `configs/`：本地凭证配置（`config.json`）与模板
- `data/`：专门存放 alpha 列表输入 JSON（如 `alpha_list.json`）
- `outputs/`：状态 CSV 输出
- `scripts/`：辅助脚本预留

## 目录核心文件

- `scripts/ace_lib.py`：BRAIN API 封装与会话管理。
- `scripts/batch_simulator.py`：批量提交、并发、轮询、状态落盘、断点续传核心逻辑。
- `data/alpha_list.json`：待回测的 alpha 列表输入文件。

## 安全凭证配置

本项目支持两种凭证来源，优先级如下：

1. `configs/config.json`（推荐本地使用）
2. 环境变量

`configs/config.json` 格式：

```json
{
   "email": "your_email@example.com",
   "password": "your_password"
}
```

如果你不想使用 `config.json`，也可以使用环境变量：

- `BRAIN_EMAIL`
- `BRAIN_PASSWORD`

PowerShell 示例：

```powershell
$env:BRAIN_EMAIL="your_email@example.com"
$env:BRAIN_PASSWORD="YOUR_CREDENTIAL"
```

## 运行方式

在当前目录执行（直接调用 `batch_simulator`）：

```powershell
python scripts/batch_simulator.py --config configs/config.json --alpha-json data/alpha_list.json --output-csv outputs/simulation_status.csv --batch-size 3 --concurrency 2 --detached
```

查询后台任务状态：

```powershell
python scripts/batch_simulator.py --status "<task_id>" --tail-lines 60
```

兼容旧路径（无需立即迁移）：

- `config.json`
- `alpha_list.json`

示例参数：

- `batch_size=3`
- `concurrency=2`
- 输出 CSV：`simulation_status.csv`

## 输出 CSV 命名规则（新增）

- 如果不传 `--output-csv`，程序会自动使用：
   - `outputs/<alpha_json文件名>_simulation_status.csv`
   - 例如：`data/alpha_list.json` → `outputs/alpha_list_simulation_status.csv`
- 因此同一个 JSON 文件会持续复用同一个 CSV（可断点续传）。
- 不同 JSON 文件名会得到不同 CSV（自动新建新任务状态文件）。
- 如果你手动传了 `--output-csv`，则以你传入的路径为准。

## 断点续传规则

断点续传依赖：

1. 输入 alpha 内容计算得到的 `fingerprint`
2. 同一个状态文件（例如 `simulation_status.csv`）

满足以下条件时会自动跳过已完成任务：

- 使用同一个状态 CSV
- alpha 内容未变化（表达式、settings、type 不变）

不影响续传：

- `alpha_list.json` 改文件名
- 输入顺序变化

会导致重跑：

- 换了状态 CSV
- 修改了 alpha 内容
- 更改了 fingerprint 计算逻辑

## 运行日志（已增强）

运行时会显示：

- 识别到多少历史完成：`Resume check: recognized X/Y ... pending Z`
- 每个批次跳过数量：`Resume detected: skipped N ...`
- 本轮汇总：`Run summary -> skipped/submitted/completed/failed`

## 输出 CSV 字段说明

主要字段：

- `fingerprint`：断点续传唯一键
- `alpha_type`：`REGULAR` / `SUPER`
- `regular_expression` / `selection_expression` / `combo_expression`
- `settings_json`：settings 完整 JSON
- `simulate_data_json`：精简回测载荷（不再重复嵌套 settings）
- `sim_id`：simulation id
- `status`：`COMPLETE` / `ERROR` / `FAIL` 等
- `alpha_id`：成功后生成的 alpha id
- `pnl` / `sharpe` / `turnover` / `fitness`
- `error` / `error_details`

## 常见问题

1. **报 429 / CONCURRENT_SIMULATION_LIMIT_EXCEEDED**
   - 程序已内置退避重试；可适当降低并发。

2. **看起来没有续传**
   - 检查是否使用同一个状态 CSV。
   - 检查输入 alpha 是否被修改。

3. **只想新开一轮独立任务**
   - 改一个新的输出 CSV 文件名即可。
