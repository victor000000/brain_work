---
name: brain-forum-browse
description: >-
  Runs live WorldQuant BRAIN Chinese forum via MCP: default **explore stroll**
  (purposeful or emergent-purpose browsing; **mandatory unique contribution** every
  session from personal + AI-chat experience). Contribute mode = stricter gap-driven
  Recon + mandatory curator. Trigger: 逛一逛论坛、逛论坛…
---

# Brain Forum Browse

## When to use (pick this skill)

**Auto-apply when the user says anything like:**

- **逛一逛论坛** / 逛论坛 / 看看论坛 / 去论坛转转
- 社区共建、填论坛空白、论坛贡献、点赞优质帖
- Agent World 论坛、PPAC 论坛、中文论坛、WorldQuant 论坛
- forum gap、browse the forum（`forum ecosystem` 为旧称，等同本 skill）

**Do not use for:** alpha 提交前审查 → use `brain-alpha-judge` (static corpus, no live forum MCP).

Forum is the live registry. **Default run = explore stroll-with-mandatory-contribution** — purposeful or emergent-purpose browsing that **always ends with a write action** (comment, post, and/or curator upvote). **No contribution-free strolls.**

## Run modes（先读这个）

| 用户意图 | 模式 | 行为 |
|----------|------|------|
| **逛一逛 / 看看 / 转转**（默认） | **explore** | stroll → **必贡献** → **auto-send E1?** 或 7.5+Contract → 6–9 |
| **贡献 / 填空白 / 跟评 / 发帖** | **contribute** | 完整 Recon → gap → 更严 write 计划 + 必 curator → Phase 7.5 → Run Contract → 同意执行 → write |
| **逛为主，可能回一句** | **hybrid**（已弃用别名） | **等同 explore** — 同样必贡献；仅用户话术不同 |

详见 [run-modes.md](references/run-modes.md)。

**禁止所有模式：** 浏览完后「你想先做哪一项？」菜单。

**Run Contract** — standard path before writes; **narrow exception:** single E1 comment/post (1 write only), zero inference → [auto-send-e1.md](references/auto-send-e1.md) (no `同意执行`).

## Minimum contribution bar（explore 每轮必达）

Every 「逛一逛论坛」session **MUST** end with a forum write. **No browse-only sessions.**

Each write must include **unique personal value** — see [unique-contribution.md](references/unique-contribution.md).

1. **≥1 evidence-backed write action** — comment **OR** new post, each claim traced to E1/E2/E3
2. **Explicit user-approved plan** with comment + curator upvote combo (when upvote is the primary action, comment still preferred when thread warrants)

**Recommended default:** ≥1 comment with **unique** E1/E2/E3 detail — not empty praise or parroting.

**If truly nothing worth saying after browse:** document why in `forum_stroll_notes.md`, then still attempt **linker-style minimal value** (helpful link, index pointer, narrow sub-question reply) — **avoid empty sessions**.

## Default: MCP 完成一切（平台 + 论坛）

**本 skill 的默认执行方式 = 全部走 MCP。** 只要涉及 BRAIN 平台或中文论坛，就必须调用 `user-brain-api` 工具 — **没有**「先凭记忆/网页/静态语料凑合」的备选路径。

| 要做的事 | 必须用的 MCP | 禁止 |
|----------|--------------|------|
| 看公告 / Theme / 比赛 | `get_messages`, `get_events` | 编造公告、读 alpha-judge 语料当 live |
| 列帖 / 搜帖 / 读帖 | 见下方 **Search 工具链** + `read_full_forum_post` | 只调 fast 就停；浏览器 |
| 术语种子 | `get_glossary_terms` | 把 glossary 锚帖当 gap 深读 |
| 用户 alpha 事实 (P5) | `get_user_alphas`（Phase 0b **默认执行**） | 编造 VF/提交记录 |
| 发帖 / 跟评 / 点赞 | `create_forum_*`, `upvote_forum_comment` | Contract 未 `同意执行` 前禁止 write；**例外：** [auto-send-e1.md](references/auto-send-e1.md) 单条 E1 |

**唯一不走 MCP 的：** skill 本地 workspace（Phase 0）、宿主 memory 文件（Phase 0a）、`agent_profile.json`（Phase 1）。这些是**工作记忆**，不是论坛真相源。

## Execution model (read this first)

```
1. Infer run_mode (default explore) — see run-modes.md
2. init_workspace --new-run; load memory; get_user_alphas (0b)
3. explore → stroll → contribution plan → forum_stroll_notes.md
   → auto-send E1? (A1–A8 + MD→HTML + chat HTML preview) → Phase 9
   OR Phase 7.5 → Run Contract → 同意执行 → Phase 6–9
4. contribute → Recon → 7.5 → Contract → 同意执行 → execute
5. follow-on impulses (optional); never post-browse menu
```

MCP: **user-brain-api** (`mcp_brain-api_*`). Default Chinese topic: **`12913416465431`**.

**Do not probe or list MCP tools at runtime** — use the exact tool names below via `CallMcpTool` (`server: user-brain-api`) or Cursor `mcp_brain-api_<name>`. Credentials come from server `user_config.json`; omit `email`/`password` unless auth fails.

**Anti-patterns:** no web fetch / Playwright / manual forum URLs; no invented post_id/title/comment; no `brain-alpha-judge` corpus as live forum substitute; no `delete_forum_*`; no simulation tools unless user explicitly pivots to alpha research.

**MCP unavailable:** report error to user and **stop** — do not improvise with browser or static files.

## Search 工具箱（多种方法，按情况选用）

平台提供 **多种 MCP 搜索/浏览方式**，Agent **按场景自行选择**（不必每次 slow）。菜单与选型见 [forum-search-strategy.md](references/forum-search-strategy.md).

| 工具 | 典型场景 |
|------|----------|
| `search_specific_forum_fast` | 中文论坛内关键词（默认首选，快） |
| `search_all_forum_slow` | fast 结果少/跨 topic/饱和检查存疑时 |
| `list_forum_posts_in_topic` | 无关键词浏览 topic |
| `list_forum_topics` | topic 发现（Phase 2） |
| `list_help_center_articles` / `get_help_center_article` | 术语表/HC 文档 |

## Available MCP tools (by phase)

| Phase | Tool | Key args | Notes |
|-------|------|----------|-------|
| 0b | `get_user_alphas` | `limit`, `stage` | P5 personal facts |
| 2 | `get_messages` | `limit=30` | Official Scan |
| 2 | `get_events` | — | competitions / themes |
| 2 | `list_forum_topics` | `max_results=50` | topic discovery |
| 2 | `get_glossary_terms` | — | Phase 2 默认 batch；seed only |
| 3–4 | `list_forum_posts_in_topic` | `topic_id=12913416465431` | browse 候选 |
| 3–4 | `search_specific_forum_fast` | `search_query`, `topic_id` | 关键词首选 |
| 3–4 | `search_all_forum_slow` | `search_query`, `locale=zh-cn` | 按需：fast 不足时 |
| 4 | `list_help_center_articles` | `max_results` | GLOSSARY_VOID / 零结果时 |
| 4 | `get_help_center_article` | `article_id` | HC 深读 |
| 6–8 | `read_forum_post` | `article_id` | short posts |
| 6–8 | `read_full_forum_post` | `article_id` | long threads + all comments |
| curator | `get_forum_comment_votes` | `post_id`, `comment_id` | pick upvote targets |

**Write (after Run Contract 同意执行):**

| L1 / role | Tool | Key args |
|-----------|------|----------|
| commenter / linker | `create_forum_comment` | `post_id`, `body` (**HTML**) |
| author | `create_forum_post` | `topic_id=12913416465431`, `title` (plain), `details` (**HTML**) |
| curator | `upvote_forum_comment` | `post_id`, `comment_id` |

**Installed but out of scope** (do not call unless user asks): `delete_forum_comment`, `delete_forum_vote`, simulation/dataset/alpha tools.

Full params: [mcp-forum-tools.md](references/mcp-forum-tools.md) · Search protocol: [forum-search-strategy.md](references/forum-search-strategy.md).

## Before first run

**Every stroll:**

```bash
python scripts/init_workspace.py --new-run
```

**Explore 首触发（逛论坛）：** 上述即可开 MCP；profile / harvest **可延后** — 见 [profile-bootstrap.md](references/profile-bootstrap.md).

**Contribute 或要固定 L2 时：**

```bash
python scripts/init_profile.py
python scripts/validate_profile.py
python scripts/harvest_external_memory.py --write   # optional if stale
```

**HTML 转换（Phase 9 前）：**

```bash
python scripts/md_to_forum_html.py --input draft.md --output submit.html
```

## Hard rules

- **Mandatory contribution every stroll (non-negotiable)**: Every session **must** end with ≥1 forum write — no browse-only exits. Each write adds **unique personal content** (your metrics, sim/debug story, angle) — **not** parrot OP/top comments, **not** empty 「感谢分享/+1」. E1 may include **host AI chat history** (P4) when specific and truthful. Linker fallback only with E2 + your index reason. See [unique-contribution.md](references/unique-contribution.md) and Minimum contribution bar above.
- **Evidence-backed writes only**: Every comment/post claim MUST trace to ≥1 source — **E1** personal experience (P0–P5 memory, sim/submission facts), **E2** MCP platform/forum data, or **E3** named external paper (arXiv ID or title+author). **Forbidden:** speculation, unfounded guesses, fabricated VF/ranks/submissions, 「我觉得可能」, vague 「研究表明」. See [evidence-and-review.md](references/evidence-and-review.md).
- **Adversarial review subagent**: Standard path — after each draft, before Contract. **Skipped** only for auto-send E1 (replaced by A1–A8 checklist). See [evidence-and-review.md](references/evidence-and-review.md), [auto-send-e1.md](references/auto-send-e1.md).
- **MCP-first default**: Phase 2–9 中凡涉及平台/论坛信息的步骤，**一律先调 MCP**；本地文件只存 MCP 结果摘要，不能代替 MCP 读取。
- **Files before MCP**: Load `outputs/workspace/` before **any** forum MCP call. Update `outputs/runs/<run_id>/session_plan.md` each phase.
- **Forum data = MCP only**: Every post title, comment body, vote count must come from MCP `read_*` / `search_*` / `list_*` — never assume from memory or static corpus.
- **Re-read before Role Pick, Draft, Act**: `session_plan.md` + first 30 lines of `forum_findings.md` (contribute) or `forum_stroll_notes.md` (explore) before draft, Run Contract, and execute.
- **Chinese only** for all forum writes. No fabricated VF, ranks, or submissions.
- **Forum submit format = HTML:** Draft in Markdown OK in notes/Contract; **`create_forum_comment.body` / `create_forum_post.details` must be forum-native HTML** before MCP write — not raw Markdown. See [write-style-zh.md](references/write-style-zh.md).
- **Run mode default explore**: 「逛论坛」= stroll-with-mandatory-contribution（有目的或 emergent）— [run-modes.md](references/run-modes.md).
- **Run Contract gate**: Standard path — planned writes need Contract + `同意执行`. **Exception:** [auto-send-e1.md](references/auto-send-e1.md) — **exactly 1** E1-only factual write, no inference → direct write after checklist.
- **Auto-execute**: 合同同意后跑完 write，不逐项菜单.
- **Curator**: **contribute** — mandatory ≥1 upvote in contract when qualified; **explore** — recommend ≥1 upvote when merited (include in contract when planned).
- **Diversity gate**: Community Similarity + Personal Uniqueness — see [content-diversity.md](references/content-diversity.md), [personal-perspective.md](references/personal-perspective.md).
- **External memory read-only** on harvest — write back to skill workspace only. See [external-memory-sources.md](references/external-memory-sources.md).
- **Search toolkit**: 论坛搜索有多种 MCP 工具 — Agent 按 [forum-search-strategy.md](references/forum-search-strategy.md) **自行选型**；不必每次 slow，也不要只知道 fast。
- **alpha-judge boundary**: rubric/corpus read-only; judge never calls live forum. See [merge-with-alpha-judge.md](references/merge-with-alpha-judge.md).
- **Follow-on impulses (additive)**: After mandatory forum contribution, record 0–3 **optional** research/exploration/skill-handoff ideas sparked by reads (technical threads, announcements, themes). **Not auto-executed**; not a post-browse menu; unverified hypotheses stay **待验证** and out of forum drafts. See [follow-on-impulses.md](references/follow-on-impulses.md).

## Pipeline（随 run_mode 裁剪）

| run_mode | 流程 |
|----------|------|
| **explore**（默认） | 0→0a→0b→1 → stroll → contribution plan → **auto-send E1?** or 7.5 → Contract? → 6–9 → follow-on |
| **contribute** | 0–5 Recon → Phase 7.5 → 1.5 Contract (STOP) → 6–9 Execute |
| **hybrid** | **同 explore**（弃用别名） |

| Phase | explore | contribute |
|-------|---------|------------|
| 0–0b | memory + MCP | same |
| 2–5 | 轻量 scan / purposeful signals（**不要求** formal gap） | 完整 gap + role pick |
| 7.5 | 标准路径必做；**auto-send E1 跳过** | same |
| 1.5 | 标准路径必做；**auto-send E1 跳过** | same |
| 6–9 | auto-send 或 **Contract 同意后** execute | 全执行 |

Templates: [forum_stroll_notes.md](templates/forum_stroll_notes.md), [run_contract.md](templates/run_contract.md).  
Details: [run-modes.md](references/run-modes.md), [mcp-by-phase.md](references/mcp-by-phase.md).

**Scout is not a role** — scan/gap in contribute mode. **L1** per session; explore stroll picks L1 at contract time from stroll findings.

## Memory stack (P0–P5)

| P | Source |
|---|--------|
| P0 | `outputs/workspace/action_ledger.json` |
| P1 | `outputs/workspace/personal_experience_memory.md` |
| P2–P3 | Project/user files (CLAUDE.md, AGENTS.md, .cursor/rules, …) |
| P4 | Session / host memories |
| P5 | BRAIN MCP facts |

Perspective Card must tag `memory_sources[]` with ≥2 layers. Details: [file-workspace.md](references/file-workspace.md).

## Quotas

See [quotas-and-cooldown.md](references/quotas-and-cooldown.md). Prefer comment over post; max 3 write actions planned per run.

## Write style

[write-style-zh.md](references/write-style-zh.md) — titles need L2 + region/dataset/operator; comments need executable detail.

**Evidence + review:** [evidence-and-review.md](references/evidence-and-review.md) — mandatory for all writes.

## Optional linker index

[index-post-protocol.md](references/index-post-protocol.md) if `index_protocol_opt_in: true`.

## References index

- **Modes:** [run-modes.md](references/run-modes.md), [run-contract.md](references/run-contract.md)
- **Unique contribution:** [unique-contribution.md](references/unique-contribution.md)
- **Follow-on:** [follow-on-impulses.md](references/follow-on-impulses.md)
- **Auto-send E1:** [auto-send-e1.md](references/auto-send-e1.md)
- **HTML convert:** `scripts/md_to_forum_html.py`
- **Evidence + review:** [evidence-and-review.md](references/evidence-and-review.md)
- Workspace: [file-workspace.md](references/file-workspace.md)
- External memory: [external-memory-sources.md](references/external-memory-sources.md)
- L2 tokens: [l2-search-tokens.md](references/l2-search-tokens.md)
- L3 signals: [l3-signal-patterns.md](references/l3-signal-patterns.md)
- Diversity: [content-diversity.md](references/content-diversity.md)
- Perspective: [personal-perspective.md](references/personal-perspective.md)
