# Evidence-Backed Writes + Adversarial Review

**Hard requirement for forum writes** — with one **narrow exception**: [auto-send-e1.md](auto-send-e1.md) (E1-only, zero inference, **exactly 1 write** — skips Phase 7.5 subagent and Run Contract; uses checklist instead).

**Standard path (default):** every explore stroll (mandatory contribution), contribute, hybrid — E1/E2/E3 + Phase 7.5 + Run Contract.

---

## Evidence tiers (every claim must map to ≥1)

| Tier | Source | Examples | Citation format |
|------|--------|----------|-----------------|
| **E1 — Personal experience** | P0–P5 memory, sim/submission history, **host AI chat history** | `get_user_alphas` metrics, `personal_experience_memory.md`, ledger notes, **Cursor/Claude/Kimi 等本机 research 对话**（具体 session/日期/任务） | `[E1: P5 get_user_alphas alpha_id=…]` / `[E1: P4 Cursor chat 2026-06-09 PPAC sim]` / `[E1: P1 §…]` |
| **E2 — Platform / forum data** | MCP-fetched live facts | `read_full_forum_post`, `search_*`, `get_messages`, `get_events`, vote counts | `[E2: MCP read_full_forum_post post_id=…]` |
| **E3 — External papers** | arXiv, published research | Named paper + author/year or arXiv ID | `[E3: arXiv:2401.12345]` or `[E3: Fama-French 1993]` |

**Rule:** Every sentence that asserts a fact, metric, recommendation, or causal claim must trace to ≥1 tier. Opinion framing without backing is **forbidden**.

### Forbidden patterns

- Speculation: 「我觉得可能」「应该会」「大概」「听说」without MCP/memory/paper source
- Fabricated VF, ranks, submission counts, Sharpe/Fitness numbers
- Vague research: 「研究表明」「有论文指出」without naming the paper
- Forum paraphrase without MCP read: quoting or summarizing a thread not fetched this run
- Memory-only alpha facts when `get_user_alphas` was available and not called
- **Parroting** thread/comment without ≥1 unique personal detail — see [unique-contribution.md](unique-contribution.md)
- Citing AI chat for metrics **not actually discussed** in that session

### Inline evidence tags (drafting)

Main agent drafts with inline tags for traceability:

```
【承接】楼主问 USA delay=1 下 PPAC turnover 怎么压。
【细节1】可试 ts_target_tvr_decay(..., target=0.35) [E1: P1 §ppac-turnover 2025-03 sim]
【细节2】同帖 @user 提到 sub-universe 失败 [E2: MCP read_full_forum_post post_id=31002256151831 comment#3]
```

Tags are stripped or softened in final Run Contract Chinese body; `evidence_sources[]` carries the audit trail.

---

## Adversarial review (standard path — mandatory per draft)

**When:** After each comment/post draft, **before** Run Contract or execute — **unless** [auto-send-e1.md](auto-send-e1.md) A1–A8 all pass (checklist only, no subagent).

**Who:** Main agent launches a **subagent** (`Task` tool, `subagent_type: generalPurpose` or `explore`).

**Cursor multitask mode:** use `Task` with `run_in_background=true` so reviews can run in parallel when multiple drafts exist.

### Workflow

```
For each comment/post draft:
1. Main agent generates draft with inline evidence tags + evidence_sources[]
2. Launch subagent with: draft text, evidence_sources[], relevant MCP excerpts, memory pointers
3. Subagent returns: PASS | REVISE with specific issues
4. Main agent revises or drops unsupported claims; re-review if major changes
5. Only PASS drafts enter Run Contract (adversarial_review_status: pass)
```

### Subagent prompt checklist

Give the subagent this rubric:

| Check | Fail if |
|-------|---------|
| Unsupported claims | Any factual/metric/causal claim without E1/E2/E3 |
| Fabricated numbers | VF, rank, Sharpe, submission count not in evidence_sources |
| Overgeneralization | 「都」「永远」「一定」without scoped evidence |
| Paper claims | E3 cited vaguely or missing arXiv/title |
| Forum appropriateness | 吹嘘、营销、空洞表扬、与楼主问题无关 |
| MCP alignment | Draft contradicts or invents content from cited post_id |
| Submit format | Body/details contain raw Markdown (`**`, `` ``` ``, `# `) instead of HTML |
| **No unique contribution** | Draft adds no personal detail beyond OP/top comments; empty praise; duplicates ledger snippets — see [unique-contribution.md](unique-contribution.md) |

### Subagent output format

```markdown
## Verdict: PASS | REVISE

### Issues (if REVISE)
1. [claim] — missing evidence / fabricated / overbroad — fix: …

### Safe to keep
- …
```

### Main agent obligations

- **REVISE** → fix every listed issue or delete the claim; re-run adversarial review if structure or metrics changed materially
- **Cannot skip** review to meet quota or deadline — **except** qualified auto-send E1 per [auto-send-e1.md](auto-send-e1.md)
- **Cannot** present Run Contract drafts to user until all planned comment/post drafts show `adversarial_review_status: pass`
- Upvote-only actions: no adversarial review on vote targets, but upvote **reason** must cite E2 (MCP read of comment quality)

---

## Integration with other gates

| Gate | Order |
|------|-------|
| Auto-send E1 eligibility | **Before** 7.5 — if pass, skip 7.5 + Contract |
| Evidence + adversarial review (Phase 7.5) | **Before** Run Contract (standard path) |
| Diversity check (Phase 8) | After drafts PASS review; may require re-review if claims change |
| Run Contract 同意执行 | Only PASS drafts with evidence_sources[] |
| Phase 9 execute | Body must match PASS draft in contract |

See [write-style-zh.md](write-style-zh.md), [run-contract.md](run-contract.md), [mcp-by-phase.md](mcp-by-phase.md).

### brain-alpha-judge boundary

- Judge rubric (read-only) informs **quality bar** — see [merge-with-alpha-judge.md](merge-with-alpha-judge.md)
- Judge static corpus is **not** E2 evidence for live claims; use MCP reads
- Pre-submit alpha review → `brain-alpha-judge`; forum writes → this skill + evidence tiers
