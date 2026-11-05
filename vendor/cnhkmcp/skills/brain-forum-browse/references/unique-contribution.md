# Unique Contribution（每逛必贡献 · 独特经验）

**Hard rule — 不可豁免：** 每次「逛论坛」session **必须** 完成至少一条 forum write（见 [run-modes.md](run-modes.md) 最低贡献条）。  
**无「今天只看看」** — linker 兜底也算 write，但仍是 **你** 的独特信息，不是空话。

---

## 必须做到

| 要求 | 说明 |
|------|------|
| **必贡献** | 每轮结束前有 MCP write（跟评/新帖；upvote 可附加但不单独满足「独特内容」） |
| **独特内容** | 正文须含 **≥1 条** 线程里尚未出现的、可执行或可追溯的个人细节 |
| **已有经验** | 来自 P0–P5，**含本机 AI 工具历史对话**（见下） |
| **不重复他人** | 禁止复述楼主/神评已说的结构、数字、操作步骤而不加新信息 |
| **不重复自己** | 禁止照搬 `action_ledger.past_contribution_snippets` 或近 5 轮同 angle_slug |

---

## E1：本机 AI 对话史（合法经验来源）

用户在本机 Cursor / Claude Code / Kimi 等与 BRAIN 相关的 **历史对话** 可作为 **E1 个人经验**，须：

1. **具体可追溯** — 注明工具 + 话题/日期/任务（非「之前聊过」）  
2. **只写对话中真实发生过的** sim 设置、报错、指标、踩坑 — 不编造对话里没有的数字  
3. **与论坛帖相关** — 对当前 thread 有增量，不是泛泛日记  

**Citation 示例：**

```
[E1: P4 Cursor chat 2026-06-09 — USA delay=1 PPAC ts_target_tvr_decay sim]
[E1: P4 agent_transcript — imb5_score coverage 排查 session]
[E1: P1 personal_experience_memory §…]  ← 若已从对话沉淀到 P1
```

**Harvest 路径（Phase 0a / 逛前）：**

- 当前 session 聊天上下文（P4 `source:session`）
- 项目 `agent-transcripts/`、Cursor 会话摘要（若可读）
- `harvest_external_memory.py` 扫到的 AGENTS.md / CLAUDE.md 中 **用户自己的 research 笔记**（非第三方教程）

见 [external-memory-sources.md](external-memory-sources.md)。

**禁止：** 把 AI 对话里的 **推测** 当事实写进论坛；对话中未出现的 Sharpe/VF 不得写。

---

## 禁止的「重复/空话」（对抗性清单）

| 禁止 | 替代 |
|------|------|
| 「感谢分享」「+1」「说得对」 | 删；若无增量 → linker 或换帖 |
| 复述楼主公式/步骤且无新数据 | 只补充 **你的** alpha_id/设置/报错/对比结果 |
| 复制神评段落改几个词 | 换 angle 或 sub-question + 你的 E1 |
| 全网泛化「提高 Sharpe 要控制 turnover」 | 绑定 region/dataset/operator + 你的数字或对话里的案例 |
| 为凑必贡献发空洞帖 | fallback linker **带 E2 读帖依据 + 你的索引/链接理由** |

---

## 贡献前自检（写入 contribution plan）

在 `forum_stroll_notes.md` / Run Contract 中必填：

```yaml
unique_contribution:
  mandatory: true  # 每轮必 true；false 则 session 失败
  thread_gap: "神评/楼主未覆盖的一点"
  my_unique_detail: "我提供的增量（一句话）"
  e1_sources:
    - "P5 get_user_alphas …" | "P4 Cursor chat …" | "P1 §…"
  not_duplicate_of:
    - "post_id=… comment#… 已说过 X"
    - "ledger snippet … 不重复"
  community_similarity: pass | revised
```

**Auto-send E1** 同样须满足「独特增量」— 仅报自己的 alpha 指标若 thread 里已有同 setting 同指标且无新信息 → **不合格**，改标准路径找角度或换帖。

---

## 与 diversity / perspective 的关系

- [content-diversity.md](content-diversity.md) — Community Similarity + angle_slug  
- [personal-perspective.md](personal-perspective.md) — Perspective Card、`personal_ok`  
- [evidence-and-review.md](evidence-and-review.md) — Phase 7.5 对抗审查须检查 **duplicate / no unique detail**

Phase 7.5 subagent 额外 FAIL 条件：

- 草稿主要是他人观点 paraphrase  
- 无 E1 指针却写「我试过」  
- 与 ledger 近 3 条 snippet 高度重叠  

---

## 汇报语气

聊天汇报须明确：**本轮已贡献**（post_id + 动作）+ **独特增量是什么**（一句）。  
不得只报「逛了这些帖」而无 write 结果。
