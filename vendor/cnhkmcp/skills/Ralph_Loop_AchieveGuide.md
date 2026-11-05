根据搜索结果，我为你整理一份完整的 **Ralph Loop 实现指南**。

---

## 一、Ralph Loop 核心原理

Ralph Loop 的本质是一个 **Bash 循环**，每次迭代都启动一个新的 AI 实例，通过外部文件（而非模型内存）来持久化状态。

### 核心循环逻辑

```bash
while true; do
  # 1. 读取 PRD 和进度文件
  # 2. 启动新的 Claude Code 实例
  # 3. 完成一个任务后退出
  # 4. 检查完成条件
  # 5. 如果未完成，继续下一轮
done
```

**关键原则：每次迭代都是全新的上下文窗口**，这样 AI 始终工作在"智能区"，不会因为上下文堆积而性能下降。

---

## 二、项目文件结构

```
your-project/
├── scripts/ralph/              # Ralph 脚本目录
│   ├── ralph.sh               # 主循环脚本
│   └── CLAUDE.md              # 每次迭代的提示词模板
├── prd.json                   # 结构化任务列表（核心）
├── progress.txt               # 学习日志（每次迭代追加）
├── CLAUDE.md / AGENTS.md      # 项目约定和模式
└── .git/                      # Git 历史作为上下文
```

---

## 三、核心文件详解

### 1. `prd.json` - 任务清单

```json
{
  "project": "MyFeature",
  "branchName": "ralph/feature-name",
  "description": "功能描述",
  "userStories": [
    {
      "id": "US-001",
      "title": "添加用户登录表单",
      "description": "作为用户，我希望能用邮箱和密码登录",
      "acceptanceCriteria": [
        "显示邮箱和密码输入框",
        "验证邮箱格式",
        "验证密码长度至少8位",
        "typecheck 通过",
        "测试通过"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "添加登录 API",
      "description": "后端登录接口",
      "acceptanceCriteria": [
        "POST /api/login 端点",
        "返回 JWT token",
        "错误处理"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    }
  ]
}
```

### 2. `scripts/ralph/CLAUDE.md` - 迭代提示词模板

```markdown
# Ralph Loop Instructions

You are an autonomous developer implementing features from a PRD.

## Your Task

1. Read `prd.json` to find the next incomplete story (`passes: false`)
2. Read `progress.txt` to learn from previous iterations
3. Read `CLAUDE.md` / `AGENTS.md` for project conventions
4. Implement the story to meet all acceptance criteria
5. Run quality checks:
   - TypeScript: `npm run typecheck` or `tsc --noEmit`
   - Tests: `npm test` (only for affected files)
   - Lint: `npm run lint` (optional)
6. If all checks pass:
   - Commit with message: "feat: [US-XXX] [story title]"
   - Update `prd.json`: set `passes: true` and add notes
   - Append learnings to `progress.txt`
   - Output: `<promise>COMPLETE</promise>`
7. If checks fail:
   - Fix the issues
   - Do NOT mark as complete
   - Output what you tried and what failed

## Rules

- ONE story per iteration
- Keep stories small (fit in one context window)
- Follow existing code patterns
- Write tests for new functionality
- Never expose secrets or credentials
```

### 3. `scripts/ralph/ralph.sh` - 主循环脚本

```bash
#!/bin/bash

# Ralph Loop - Autonomous AI Development
# Usage: ./ralph.sh [max_iterations] [--tool claude|amp|opencode]

set -euo pipefail

# 配置
MAX_ITERATIONS=${1:-10}
TOOL=${2:-"claude"}
PROMPT_FILE="scripts/ralph/CLAUDE.md"
PRD_FILE="prd.json"
PROGRESS_FILE="progress.txt"
COMPLETION_PROMISE="<promise>COMPLETE</promise>"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
  echo -e "${GREEN}[RALPH]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_deps() {
  if ! command -v jq &> /dev/null; then
    error "jq is required. Install with: brew install jq"
    exit 1
  fi

  if [[ "$TOOL" == "claude" ]] && ! command -v claude &> /dev/null; then
    error "Claude Code not found. Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
  fi
}

# 检查是否有未完成的任务
has_incomplete_tasks() {
  local incomplete
  incomplete=$(jq '[.userStories[] | select(.passes == false)] | length' "$PRD_FILE")
  [[ "$incomplete" -gt 0 ]]
}

# 获取下一个任务
get_next_task() {
  jq -r '.userStories[] | select(.passes == false) | .id' "$PRD_FILE" | head -1
}

# 运行一次迭代
run_iteration() {
  local iteration=$1
  local task_id
  
  log "=== Iteration $iteration / $MAX_ITERATIONS ==="
  
  if ! has_incomplete_tasks; then
    log "All tasks complete!"
    return 0
  fi
  
  task_id=$(get_next_task)
  log "Working on: $task_id"
  
  # 创建临时文件捕获输出
  local output_file
  output_file=$(mktemp)
  
  # 运行 Claude Code
  # -p 表示非交互式模式，直接执行
  if [[ "$TOOL" == "claude" ]]; then
    claude -p "$(cat "$PROMPT_FILE")" 2>&1 | tee "$output_file"
  elif [[ "$TOOL" == "amp" ]]; then
    amp --prompt "$(cat "$PROMPT_FILE")" 2>&1 | tee "$output_file"
  else
    error "Unknown tool: $TOOL"
    return 1
  fi
  
  # 检查完成承诺
  if grep -q "$COMPLETION_PROMISE" "$output_file"; then
    log "Task completed successfully"
  else
    warn "Task may not be complete (no completion promise found)"
  fi
  
  rm -f "$output_file"
  
  return 0
}

# 主循环
main() {
  log "Starting Ralph Loop"
  log "Max iterations: $MAX_ITERATIONS"
  log "Tool: $TOOL"
  
  check_deps
  
  # 检查必要文件
  if [[ ! -f "$PRD_FILE" ]]; then
    error "PRD file not found: $PRD_FILE"
    exit 1
  fi
  
  if [[ ! -f "$PROMPT_FILE" ]]; then
    error "Prompt file not found: $PROMPT_FILE"
    exit 1
  fi
  
  # 初始化 progress.txt
  if [[ ! -f "$PROGRESS_FILE" ]]; then
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
  fi
  
  # 运行循环
  local iteration=1
  while [[ $iteration -le $MAX_ITERATIONS ]]; do
    if ! has_incomplete_tasks; then
      log "All tasks completed in $((iteration - 1)) iterations!"
      exit 0
    fi
    
    run_iteration $iteration
    
    iteration=$((iteration + 1))
    
    # 短暂暂停，避免 API 限制
    sleep 2
  done
  
  log "Max iterations reached ($MAX_ITERATIONS)"
  log "Remaining tasks:"
  jq -r '.userStories[] | select(.passes == false) | "  - \(.id): \(.title)"' "$PRD_FILE"
  
  exit 2
}

main "$@"
```

---

## 四、工作流程

### Step 1: 创建 PRD（产品需求文档）

在 Claude Code 中使用 PRD Skill：

```
Load the prd skill and create a PRD for [你的功能描述]
```

Claude 会询问澄清问题，然后生成 `prd.md`。

### Step 2: 转换为 JSON 格式

```
Load the ralph skill and convert prd.md to prd.json
```

这会生成结构化的 `prd.json` 文件。

### Step 3: 运行 Ralph Loop

```bash
# 基础用法（默认 10 次迭代）
./scripts/ralph/ralph.sh

# 指定最大迭代次数
./scripts/ralph/ralph.sh 25

# 使用 AMP CLI 替代 Claude Code
./scripts/ralph/ralph.sh 25 amp
```

### Step 4: 监控进度

查看以下文件了解进展：
- `prd.json` - 查看哪些任务已完成
- `progress.txt` - 查看每次迭代的学习记录
- `git log` - 查看提交历史

---

## 五、进阶实现

### 1. 带 Stop Hook 的增强版（单会话模式）

如果你希望在一个 Claude Code 会话内循环（使用 Stop Hook）：

```bash
#!/bin/bash
# ralph-stop-hook.sh

PROMPT_FILE="scripts/ralph/CLAUDE.md"
MAX_ITERATIONS=${1:-10}

for i in $(seq 1 $MAX_ITERATIONS); do
  echo "=== Iteration $i / $MAX_ITERATIONS ==="
  
  # 使用 --continue 继续同一会话
  # Claude Code 的 stop hook 会拦截退出并重新注入提示词
  claude --continue -p "$(cat "$PROMPT_FILE")"
  
  # 检查是否完成
  if ! jq -e '[.userStories[] | select(.passes == false)] | length > 0' prd.json > /dev/null; then
    echo "All tasks complete!"
    exit 0
  fi
done
```

**注意**：官方推荐 **Bash 循环模式**（每次新会话），因为单会话模式会导致上下文堆积。

### 2. 带监控面板的版本

```bash
# 使用 tmux 创建监控会话
ralph --monitor
```

这会创建两个面板：
- 左侧面板：运行 Ralph Loop
- 右侧面板：实时显示进度

### 3. 多 Agent 支持版本

```bash
# ralph-wiggum 多 Agent 版本
ralph "你的任务描述" --agent claude-code --max-iterations 20
ralph "你的任务描述" --agent codex --max-iterations 20
ralph "你的任务描述" --agent opencode --max-iterations 20
```

---

## 六、最佳实践

### ✅ 应该做的

1. **从 HITL 模式开始**
   ```bash
   # 先手动运行几次，观察行为
   ./ralph.sh 3
   ```

2. **设置合理的迭代限制**
   ```bash
   # 小型任务：5-10 次
   # 中型任务：20-30 次
   # 大型任务：50 次
   ./ralph.sh 20
   ```

3. **保持任务小巧**
   - 每个用户故事应该在一个上下文窗口内完成
   - 优先处理架构和高风险任务

4. **使用 Git 分支**
   ```bash
   git checkout -b ralph/feature-name
   ```

5. **定义明确的完成标准**
   ```json
   "acceptanceCriteria": [
     "typecheck 通过",
     "测试覆盖率 > 80%",
     "所有测试通过"
   ]
   ```

### ❌ 不应该做的

1. **不要在生产环境直接运行**
   - 始终在分支上运行
   - 审查所有提交后再合并

2. **不要暴露敏感信息**
   - 确保 `.env` 文件在 `.gitignore` 中
   - 不要在 PRD 中包含 API 密钥

3. **不要设置过大的迭代次数**
   - 这会导致意外的高成本

4. **不要跳过测试验证**
   - 确保验收标准包含自动化测试

---

## 七、完整示例项目

```
my-project/
├── scripts/
│   └── ralph/
│       ├── ralph.sh          # 主循环脚本
│       └── CLAUDE.md         # 迭代提示词
├── prd.json                  # 任务清单
├── progress.txt              # 学习日志
├── CLAUDE.md                 # 项目约定
├── src/                      # 源代码
└── tests/                    # 测试文件
```

**运行命令：**

```bash
# 1. 进入项目目录
cd my-project

# 2. 确保在正确的分支
git checkout -b ralph/my-feature

# 3. 运行 Ralph Loop
./scripts/ralph/ralph.sh 25

# 4. 监控进度（另一个终端）
tail -f progress.txt

# 5. 完成后审查
git log --oneline
git diff main
```

---

## 八、开源实现参考

| 项目 | 特点 | 链接 |
|------|------|------|
| **ralph-wiggum** | 官方实现，支持 Claude/AMP/OpenCode | [GitHub](https://github.com/snarktank/ralph) |
| **open-ralph-wiggum** | 多 Agent 支持，CLI 工具 | [GitHub](https://github.com/Th0rgal/open-ralph-wiggum) |
| **ralphctl** | Rust 实现，更强大的 CLI | [GitHub](https://github.com/wcygan/ralphctl) |
| **ralph-claude-code** | 带监控面板的完整方案 | [GitHub](https://github.com/frankbria/ralph-claude-code) |

---

## 总结

Ralph Loop 的实现非常简单，核心就是：

1. **Bash 循环** - 每次迭代启动新的 AI 实例
2. **外部状态** - 通过 `prd.json` 和 `progress.txt` 持久化
3. **完成承诺** - AI 输出 `<promise>COMPLETE</promise>` 表示完成
4. **质量门禁** - 每次迭代运行测试和类型检查

最简单的实现只需要几十行 Bash 脚本，但威力巨大——已经被用于：
- 14 小时的 React 升级
- 完整的端到端应用开发
- 大规模测试迁移