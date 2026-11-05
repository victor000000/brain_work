# Claude Code Skill 撰写指南

本指南基于 Claude Code 官方文档整理，旨在帮助开发者快速掌握 Agent Skill (技能) 的创建与管理方法。

## 1. 什么是 Skill？

Skill 是一个 Markdown 文件，用于“教会” Claude 如何执行特定任务（如按特定标准审查代码、生成 Git 提交信息等）。
- **自动触发**：当用户的请求匹配 Skill 的 `description` 时，Claude 会自动应用该 Skill。
- **作用域**：可以在个人层面（跨项目）或项目层面（特定仓库）定义。

## 2. 目录结构与存放位置

### 存放位置
- **个人 Skill** (所有项目可用): `~/.claude/skills/<skill-name>/`
- **项目 Skill** (仅当前项目可用): `.claude/skills/<skill-name>/`

### 文件结构示例
一个标准的 Skill 目录结构如下：
```text
my-skill/
├── SKILL.md           # [必需] 核心定义文件
├── reference.md       # [可选] 详细参考文档（渐进式加载）
├── examples.md        # [可选] 示例库
└── scripts/           # [可选] 工具脚本
    └── helper.py
```

## 3. 编写 SKILL.md

`SKILL.md` 是 Skill 的核心，由 **YAML Frontmatter (元数据)** 和 **Markdown 正文 (指令)** 组成。

### YAML Frontmatter 参数

```yaml
---
name: my-skill-name        # [必需] 技能名称 (小写字母、数字、连字符，max 64字符)
description: >-            # [必需] 描述技能功能及触发时机 (max 1024字符)。
                           # Claude 依靠此描述决定何时调用该 Skill。
                           # 务必包含用户可能会用到的关键词。
allowed-tools:             # [可选] 限制该 Skill 可用的工具
  - Read
  - Grep
user-invocable: true       # [可选] 是否在 slash (/) 命令菜单中显示。默认为 true。
context: fork              # [可选] 设为 fork 可在隔离的子 Agent 环境中运行
agent: general-purpose     # [可选] 配合 context: fork 使用，指定 Agent 类型
hooks:                     # [可选] 定义生命周期钩子
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

### Markdown 正文

正文部分是给 Claude 的具体操作指南。

```markdown
# My Skill Name

## Instructions (指令)
清晰、分步骤地告诉 Claude 该怎么做。
1. 第一步...
2. 第二步...

## Examples (示例)
提供具体的输入输出示例，帮助 Claude 理解预期效果。

## Utility Scripts (工具脚本)
如果需要执行复杂逻辑，可以引用 scripts 目录下的脚本：
Run the validation script:
python scripts/validate.py input.txt
```

## 4. 最佳实践：渐进式披露 (Progressive Disclosure)

为了节省 Context Window（上下文窗口），不要将所有内容都塞进 `SKILL.md`。

1. **核心文件 (`SKILL.md`)**：仅包含最核心的指令和导航。
2. **支持文件**：将详细的 API 文档、长篇示例放入 `reference.md` 或 `examples.md`。
3. **引用方式**：在 `SKILL.md` 中使用相对链接引用支持文件。Claude 会在需要时读取它们。
   - `For API details, see [reference.md](reference.md)`

## 5. 高级配置

### 限制工具权限 (`allowed-tools`)
如果你希望 Skill 只能读取文件而不能修改，可以限制其权限：
```yaml
allowed-tools:
  - Read
  - Grep
  - Glob
```

### 钩子 (Hooks)
可以在工具使用前后执行特定操作，例如安全检查：
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/check.sh"
          once: true
```

## 6. 测试与调试

1. **验证加载**：
   在 Claude Code 中输入：`What Skills are available?`
   如果列表中出现了你的 Skill，说明加载成功。

2. **触发测试**：
   根据你写的 `description` 提出请求。
   例如描述是 "Explains code with diagrams"，则输入 "How does this code work?"。
   Claude 应提示使用该 Skill。

3. **故障排查**：
   - **不触发**：检查 `description` 是否不够具体？是否包含了用户会说的关键词？
   - **不加载**：检查文件名是否严格为 `SKILL.md` (大小写敏感)？YAML 格式是否正确？
   - **调试模式**：使用 `claude --debug` 启动以查看加载错误。

## 7. 示例：解释代码 Skill

**位置**: `~/.claude/skills/explaining-code/SKILL.md`

```yaml
---
name: explaining-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works or when the user asks "how does this work?".
---

When explaining code, always include:

1. **Start with an analogy**: Compare the code to something from everyday life.
2. **Draw a diagram**: Use ASCII art to show the flow.
3. **Walk through the code**: Explain step-by-step.
4. **Highlight a gotcha**: Common mistakes.
```
