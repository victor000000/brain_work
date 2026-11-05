# reference.md

## 参数说明

### `scripts/run.py`
- `--config`: 配置文件路径，默认 `configs/config.json`
- `--idea-json`: single 模式输入
- `--idea-json-list`: cross 模式输入（2个及以上）
- `--template-text`: single 直接文字输入（模板正文）
- `--idea-text`: single 直接文字输入的 idea 描述（可选）
- `--template-text-2`: cross 直接文字输入的第二个模板
- `--idea-text-2`: cross 直接文字输入的第二个 idea 描述（可选）
- `--manual-templates-json`: cross 直接文字输入数组，格式 `[{"template":"...","idea":"..."}, ...]`
- `--dataset-id`: 直接文字输入必填（用于构造标准 idea 文件名）
- `--region`: 直接文字输入必填（用于构造标准 idea 文件名）
- `--delay`: 直接文字输入必填（用于构造标准 idea 文件名）
- `--data-type`: `MATRIX` 或 `VECTOR`
- `--cross-prompt-style`: `conservative|balanced|aggressive|ultra-aggressive`
- `--feature-implementation-dir`: 覆盖默认依赖目录
- `--template-enhance-dir`: 覆盖知识文件目录
- `--idle-timeout-seconds`: 无输出超时阈值
- `--detached`: 后台启动，命令立即返回
- `--task-id`: 指定后台任务ID（可选）
- `--tasks-dir`: 后台任务目录根（默认 `outputs/tasks`）
- `--status`: 按 `task_id` 查询后台任务状态并退出
- `--tail-lines`: `--status` 时输出日志尾部行数（默认 40）
- `--dry-run`: 仅校验与打印，不执行

## 默认路径策略

优先使用本技能下本地依赖：
- `brain-feature-implementation/`

可通过 `--feature-implementation-dir` 强制覆盖。

## 直接文字输入约束（对齐前端提示）

1. `template` 建议包含 `{}` 数据字段占位（例如 `{ret}`）。
2. `idea` 建议填写（前端文案标注为必填）。
3. `dataset-id` 建议同时包含字母和数字（例如 `fundamental28`）。
4. `region` 建议使用区域缩写（如 `GLB/USA/CHN`）。
5. `delay` 需为整数，建议范围 `0-10`。
6. cross 手动输入至少需要 2 组 template。

## 长任务排障

### A. 命令超时
1. 先检查产物是否已生成
2. 若产物在更新，继续等待
3. 仅当产物无变化且进程退出，再判失败

### A1. 后台任务监控
1. 启动后记录控制台返回的 `task_id` 与 `pid`
2. 直接查询状态：`python scripts/run.py --status <task_id>`
3. 查看日志：`outputs/tasks/<task_id>/stdout.log`
4. 如需查看错误：`outputs/tasks/<task_id>/stderr.log`
5. 可用 `--tail-lines` 调整查询输出的日志行数
4. 如需确认进程：PowerShell 使用 `Get-Process -Id <pid>`

### B. `enhanced_final_expressions` 为空
1. 检查实现阶段是否产出 `*_idea_*.json`
2. 检查模板占位符是否存在于数据集字段
3. 检查 validator 是否过滤全部表达式
4. 可切换 `--cross-prompt-style conservative` 降低占位符漂移风险

### C. 数据集拉取失败
- 确认 `BRAIN` 凭证有效
- 确认目标 `dataset/region/delay` 可访问
- 若遇限流，重试并观察已有 CSV 是否可复用

## 输出说明

输出写回 primary idea 同目录：
- `enhanced_templates_<ts>.json`
- `enhanced_final_expressions_<ts>.json`

直接文字输入模式会先在 `outputs/` 下生成临时 idea json，再按同样流程运行；最终输出写回该临时 idea 的目录。

`enhanced_final_expressions` 是去重 + 规范化 + validator 过滤后的结果。
