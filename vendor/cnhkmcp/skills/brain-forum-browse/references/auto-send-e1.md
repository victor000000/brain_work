# Auto-Send E1（单条跟评/新帖 — 免 Run Contract）

当且仅当草稿**完全是可核验的一手经验复述**时，可跳过 Run Contract 与 Phase 7.5 对抗 subagent，**直接 MCP write**。  
任一条件不满足 → **立刻回退**标准路径（7.5 + Run Contract + `同意执行`）。

**无字数限制** — 仅限制 **条数：本轮恰好 1 条 write**（跟评或新帖二选一）。

---

## 适用场景（抽象，非固定模板）

- 「我这边 alpha_id=… delay=1 region=USA IS Sharpe/Fitness/turnover 是 …（本轮 `get_user_alphas` 可查）」  
- 「同设定下我 2025-03 sim 记录：…（P1 / ledger 有日期与 alpha_id）」  
- 新帖：**仅**分享本人某条 Alpha 的可验证结果或踩坑记录，不对他人做建议或因果推断  

**不适用：** 对他人「你可以试试」、引用公告解读、论文、Linker、提问式跟评、**多条 write**、点赞。

---

## 硬性条件（ALL must pass）

| # | 条件 |
|---|------|
| A1 | **恰好 1 条 write**：`create_forum_comment` **或** `create_forum_post`（不含 upvote；同轮不得再有第二条 write） |
| A2 | **E1-only + unique:** 每条事实主张来自 E1 源；且含 **≥1 条** thread 中尚未覆盖的个人细节（不可仅复述楼主/神评） |
| A3 | **E1-only sources:** 仅来自本轮 `get_user_alphas`、P1、P0 ledger、**P4 本机 AI 对话**（须具体 session/日期/任务）。**禁止 E2/E3 作为正文论据** |
| A4 | **零推断：** 正文不得出现对他人有效的建议、预测、因果归纳。禁用词包括但不限于：建议、推荐、可能、应该、或许、大概、预计、试试、更好、能提升、有助于 |
| A5 | **第一人称过去/现在事实：** 只陈述「我 / 我的 alpha / 我的 sim」已发生且可核对的结果；不评价楼主方案对错 |
| A6 | **本轮 P5 已拉：** 若草稿含任何 alpha 指标，本 run 必须已调用 `get_user_alphas`；不得凭 memory 编造数字 |
| A7 | **无 open question：** 不得用跟评主文向楼主提问（提问属推断/延伸，走 Contract） |
| A8 | **新帖额外：** saturation **ALLOW**（MCP 查重）；标题须为「经验记录」而非教程/倡议 |

**Upvote 永不 auto-send** — 始终 Run Contract。

---

## 与标准路径对比

| | Auto-send E1 | 标准（默认） |
|--|--------------|--------------|
| 条数 | **恰好 1 条 write** | 可多条约（≤ quota） |
| 证据 | 仅 E1，可核验 | E1 / E2 / E3 |
| Phase 7.5 subagent | **跳过**（用下方清单自检） | **必做** |
| Run Contract | **跳过** | **必做** + `同意执行` |
| 聊天 | write **前**贴 HTML 预览 | Contract 内 HTML + `同意执行` |
| 推断/建议 | **禁止** | 允许若有 E1/E2/E3 |

---

## 自检清单（代替 7.5 — 主 agent 写前必过）

在 `session_plan.md` 记录 `auto_send_certification: true` 前，逐项 ✓：

```
- [ ] A1–A8 全部满足
- [ ] 每个数字能在 get_user_alphas 响应或 P1/ledger 指针中找到一一对应
- [ ] 删除所有对他人的建议句；若删后无实质内容 → 放弃 auto，改 Contract
- [ ] 已 MCP read 目标帖（程序需要，正文不引用他人观点作论据）
- [ ] 新帖：saturation ALLOW 已记录
- [ ] 若有任何犹豫 → auto_send_certification: false → 标准路径
```

**禁止：** 为省事强行 auto；把 E2 公告/他帖观点塞进 auto 草稿。

---

## 执行流程

```
explore/contribute 逛读 → 定 contribution
  → 评估 auto-send 资格
  → 若 PASS：写 certification → MD→HTML（`scripts/md_to_forum_html.py` 或等价）→ **聊天贴 HTML 预览** → Phase 9 write（1 条）→ 汇报 + 延伸想法
  → 若 FAIL：Phase 7.5 → Run Contract → 同意执行 → Phase 9
```

同轮若还计划 **第 2 条 write 或 upvote** → 整条路径按**标准 Contract**（auto 仅适用于「本轮仅此 1 条 E1 write」）。

---

## 日志（必填）

`session_plan.md`：

```yaml
auto_send_e1:
  eligible: true | false
  certification: pass | fallback_to_contract
  reason_if_fallback: "…"
  write_type: comment | post
  post_id: …  # comment target or new post after create
  e1_pointers:
    - "P5 get_user_alphas alpha_id=… field=sharpe"
    - "P1 personal_experience_memory §…"
```

`action_ledger.json`：标记 `auto_send_e1: true`。

---

## 示例（合格 vs 不合格）

**合格（auto）：**  
「同帖提到的 delay=1 USA，我 alpha `abc123` 当前 IS Sharpe 1.05、Fitness 0.82、turnover 0.31（刚查平台）。设置：TOP3000、neutralization=SUBINDUSTRY。」（长短不限，只要 E1-only、零推断）

**不合格 → Contract：**  
「建议你也试 ts_target_tvr_decay…」— 含建议  
「公告说 backfill 不计 operator 数，所以你应该…」— E2 + 建议  
「warm-start 可能更好」— 推断  
「楼主对比过冷启动吗？」— 提问  
两条跟评 — 违反 A1  

---

## Config

`configs/config.example.json`:

```json
"auto_send_e1": {
  "enabled": true,
  "max_writes": 1,
  "require_get_user_alphas_this_run": true
}
```

`consent_mode` 仍为 `upfront_batch` 作为默认；auto-send 是**窄例外**，不是新菜单选项。
