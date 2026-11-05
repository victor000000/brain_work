# brain-enhance-template

将 `APP/trailSomeAlphas` 的 enhance 能力隔离为可命令行运行的 headless 技能。

## 目录结构

- `SKILL.md`：技能入口定义（自动触发描述 + 操作规范）
- `reference.md`：详细参数、故障排查、长任务检查清单
- `examples.md`：触发示例与命令示例
- `scripts/run.py`：统一入口（建议唯一执行入口）
- `scripts/enhance_template.py`：增强核心流程
- `brain-feature-implementation/`：本地依赖副本（implement / validator / data）
- `configs/config.json`：凭证与模型配置
- `knowledge/template_final_enhance/`：增强提示词知识文件
- `testingTemplate/`：测试输入样本

## 使用

### 输入提示（对齐前端）
- `template`：建议把可变数据字段写成 `{}` 占位形式（例如 `{ret}`）。
- `idea`：建议填写自然语言思路描述（前端文案将其标注为必填）。
- `dataset-id`：建议同时包含字母与数字（例如 `fundamental28`）。
- `region`：建议使用标准区域缩写（例如 `GLB/USA/CHN`）。
- `delay`：整数，建议范围 `0-10`。
- cross 手动输入：至少提供 2 组 template（可继续添加更多组）。

### 1) 准备配置
编辑 `configs/config.json` 并填充：
- `brain_email`
- `brain_password`
- `moonshot_api_key`

### 2) Single 模式
```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --idea-json "<idea_json_path>" --data-type MATRIX --detached
```

### 3) Cross 模式
```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --idea-json-list "<idea1.json>" "<idea2.json>" --cross-prompt-style balanced --data-type MATRIX --detached
```

### 4) Single 直接文字输入
```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --template-text "<template_text>" --idea-text "<idea_text_optional>" --dataset-id "fundamental72" --region "GLB" --delay 1 --data-type MATRIX --detached
```

### 5) Cross 直接文字输入
```powershell
# 在 brain-enhance-template 根目录执行
python scripts/run.py --config configs/config.json --manual-templates-json "[{\"template\":\"<t1>\",\"idea\":\"<i1>\"},{\"template\":\"<t2>\",\"idea\":\"<i2>\"}]" --dataset-id "fundamental72" --region "GLB" --delay 1 --cross-prompt-style balanced --data-type MATRIX --detached
```

PowerShell 更稳的等价写法：

```powershell
python scripts/run.py --config configs/config.json --template-text "<t1>" --idea-text "<i1>" --template-text-2 "<t2>" --idea-text-2 "<i2>" --dataset-id "fundamental72" --region "GLB" --delay 1 --cross-prompt-style balanced --data-type MATRIX --detached
```

## 长任务说明

- 默认按长任务处理，建议后台模式 `--detached`，避免外层会话超时杀进程。
- 后台日志位于 `outputs/tasks/<task_id>/stdout.log` 与 `stderr.log`。
- 先检查输出目录中是否已生成：
  - `enhanced_templates_*.json`
  - `enhanced_final_expressions_*.json`
- 如果 final expressions 为空，优先检查：
  - 模板占位符是否与数据集字段匹配
  - implement 阶段是否有产出
  - validator 是否过滤掉全部表达式

详细说明见 [reference.md](reference.md) 与 [examples.md](examples.md)。
