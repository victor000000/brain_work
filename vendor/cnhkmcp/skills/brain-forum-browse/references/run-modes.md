# Run Modes（逛论坛 = 必贡献 stroll）

「逛一逛论坛」**默认 = explore stroll-with-mandatory-contribution** — 有方向地逛或先逛后定方向，**每轮必须以贡献收尾**。  
禁止的是：浏览后的「你想先做哪一项？」菜单，以及**零贡献**的纯 read 会话。

Agent 先 **推断本轮模式**（可一句话向用户确认，但不要菜单式「选 A/B/C/D」）。

---

## 三种模式

| 模式 | 用户典型说法 | 做什么 | Run Contract? |
|------|--------------|--------|---------------|
| **explore**（默认） | 逛一逛、看看、转转、随便看看、有啥好玩的 | 有/无起点 MCP 搜读 → **必贡献** → **auto-send E1** 或 7.5+Contract → 6–9 | **单条 E1 write 可免**；否则必做 |
| **contribute** | 贡献、填空白、跟评、发帖、点赞、社区共建 | 完整 Recon → gap → 更严 write 计划 + **必 curator** → Phase 7.5 → Run Contract → 同意执行 | **必做** |
| **hybrid**（弃用别名） | 逛一逛顺便看看要不要回 | **等同 explore** — 同样必贡献、同样 pipeline；仅用户话术暗示「可能回」 | **每轮必做** |

**默认规则：** 用户只说了「逛论坛」且未提贡献 → **`explore`**（仍**必须**以贡献收尾）。

---

## Minimum contribution bar（explore 每轮必达 — **硬性，无例外**）

Every 「逛一逛论坛」session **MUST** end with a forum write. **「只逛不贡献」= session 失败.**

Every write **MUST** add **unique personal value** — not parrot OP or top comments. Draw from P0–P5 **including host AI chat history** (Cursor/Claude/Kimi research sessions). See [unique-contribution.md](unique-contribution.md).

Every explore stroll session MUST meet **at least one** of:

1. **≥1 evidence-backed write action** — comment **OR** new post, each claim traced to E1/E2/E3
2. **Explicit user-approved plan** with comment + curator upvote combo (when upvote is the primary action, comment still preferred when thread warrants)

**Recommended default:** ≥1 comment with **unique** E1/E2/E3 detail (your alpha, your AI-chat sim case, or your audit) — not empty praise; consider 1 curator upvote when merited.

**If truly nothing worth saying after browse:** document why in stroll notes, then still attempt **linker-style minimal value** (helpful link, index pointer, narrow sub-question reply) — **avoid empty sessions**.

---

## explore 模式（stroll-with-mandatory-contribution — 两种子风格）

**目标：** 像研究员逛社区 — 有研究感、不打卡式交作业；**贡献是终点，不是可选项**。

### 子风格 A — 有目的逛（purposeful stroll）

起步即有方向，来自（不必全做，按 relevance 选）：

- P5 / `get_user_alphas` — 近期 alpha 表现、提交状态
- `get_messages`, `get_events` — 公告、Theme、比赛
- 置顶帖 / Official Scan 轻量信号（不必 formal gap 打分）
- P0–P4 memory — 用户当前 research 焦点
- 用户本轮聊天上下文

→ MCP 搜读围绕这些信号；笔记里写清 **starting intent**。

### 子风格 B — 先逛后定方向（emergent-purpose stroll）

起步无固定 agenda；先 `list_*` / `search_*` / `read_*` 跟着好奇心逛。  
逛出 interesting finds 后，在笔记里记录 **emerged contribution plan**（跟评/发帖/点赞 — **必有一项**）。

### 共同流程

```
1. Load memory (P0–P5) + 平台信号（performance / messages / events / pinned）
2. MCP 探索（search 工具箱 + list + read，Agent 自选）
3. 跟着好奇心或起步方向：热帖、公告、神评论、冷门但契合 memory 的帖
4. 输出「逛论坛笔记」+ **必填 contribution plan**
5. Phase 7.5 — **或** [auto-send-e1.md](auto-send-e1.md) 自检（**单条** E1 write、零推断）
6. Phase 1.5 — Run Contract（**auto-send 跳过**）→ **同意执行**
7. Phase 6–9 执行
```

**汇报风格（示例结构，可灵活）：**

- 🔥 今日亮点（1–3 条，为什么对你有趣）
- 📌 和你 research 的交集（引用 memory_sources）
- 🧵 值得深读（post_id + 一句 hook）
- 💡 意外发现 / 好玩的点（允许轻松语气）
- ✍️ **本轮贡献计划** → auto-send E1 **或** Run Contract → 同意执行（不要菜单）
- 🔭 **延伸想法（可选）** — 执行贡献**之后**汇报：研究 hook / Theme 对齐 / skill handoff；**不自动开 sim 或别的 skill** — 见 [follow-on-impulses.md](follow-on-impulses.md)

**explore 下禁止：**

- **零贡献**纯 read 会话
- 为写而写的空洞跟评（无 E1/E2/E3）
- 「你想先做哪一项」菜单
- 未计划 write 却硬跑完整 gap Recon + Role Pick upfront
- 跳过 Run Contract 直接 write（**除非** [auto-send-e1.md](auto-send-e1.md) 全过）

**explore 下允许：**

- 只深读 1 篇但读透后写 1 条高质量跟评
- 搜多个 angle 做对比后选最佳贡献点
- linker-style 最小价值（链接/索引指针）当强观点不足时
- **推荐** curator upvote 当合同计划了且评论值得推

**explore vs contribute 区别（同必贡献，不同严格度）：**

| 维度 | explore | contribute |
|------|---------|------------|
| 起步 | purposeful 或 emergent | 用户明确 gap 驱动 |
| Recon 2–5 upfront | 不要求 formal gap | 完整 gap 评分 + Role Pick |
| Curator | 推荐（合同含 upvote 时执行） | **必** ≥1 upvote（无合格则说明） |
| Write 计划 | 逛中/逛后定 1–3 动作 | 更丰富的多 gap 计划 |
| Run Contract | 标准路径必做；**auto-send E1 免** | **必做** |

---

## contribute 模式

用户**明确**要**以 gap 驱动留下痕迹**时，走 [run-contract.md](run-contract.md)：

```
Recon (0–5) → Phase 7.5 → Run Contract (1.5, STOP) → Execute (6–9)
```

合同含：搜/读/评/赞/帖 + 中文草稿 + **必 curator**（有合格目标时）；**同意执行** 后自动完成，不再逐项菜单。

比 explore **更严**：upfront formal gap、Role Pick、curator 块默认必填。

---

## hybrid 模式（弃用别名）

**`hybrid` = `explore`** — 同一 pipeline、同一最低贡献条、同一 Run Contract 门。

用户说「逛…顺便…/看看要不要回」→ 仍推断 **`explore`**（或显式记 `hybrid` 别名，行为不变）。

历史原因：旧版 hybrid 暗示「write 可选」；**已废除**。不要因 hybrid 话术降低贡献要求。

---

## 模式推断（Agent 自行判断）

| 信号 | 模式 |
|------|------|
| 仅「逛/看/转转/有啥」 | explore |
| 「贡献/回复/发帖/点赞/填空白」 | contribute |
| 「逛…顺便…/看看要不要回」 | explore（hybrid 别名，行为同 explore） |
| 上一轮 explore 用户说「那个帖帮我评一下」 | Run Contract（单帖即可；不必重标 contribute） |

不确定时：**默认 explore**，笔记末尾写 contribution plan → Run Contract — **不等用户选菜单**。

---

## 与硬规则的关系

| 规则 | explore | contribute |
|------|---------|------------|
| MCP-only | ✓ | ✓ |
| **Mandatory contribution** | **✓** | **✓** |
| **Evidence-backed writes (E1/E2/E3)** | **✓** | **✓** |
| **Adversarial review subagent (Phase 7.5)** | **✓** | **✓** |
| Memory / 平台信号驱动方向 | ✓（purposeful 硬一点，emergent 软一点） | ✓ 硬规划 + formal gap |
| Formal gap Recon 2–5 upfront | ✗ 不要求 | ✓ |
| Curator | 推荐（合同含 upvote） | ✓ 必（合同内） |
| Diversity gate | ✓ | ✓ |
| Run Contract | **每轮必做**（仅 PASS 草稿） | **每轮必做** |
| 禁止事后菜单 | ✓ | ✓ |

**所有模式的 write**（explore、contribute、hybrid 别名）均须证据支撑 + 对抗审查 — 见 [evidence-and-review.md](evidence-and-review.md)。

Config: `"default_run_mode": "explore"` — explore = stroll-with-mandatory-contribution, not read-only.
