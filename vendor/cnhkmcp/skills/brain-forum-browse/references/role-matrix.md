# Role Matrix

## L1 per session (pick one)

| L1 | When | Write actions |
|----|------|---------------|
| commenter | UNANSWERED, UNDERSERVED, STALE_FAQ | 1–3 中文跟评 |
| author | TOPIC_VOID, GLOSSARY_VOID, saturation ALLOW | 0–1 中文新帖 |
| linker | dup cluster, index opt-in, author BLOCK | 带链接跟评 / 索引 |

**Scout is not L1** — scan/gap built into **contribute** pipeline. Explore **does not require** upfront formal gap scoring; purposeful signals from scan/memory may inform stroll direction. Every explore stroll picks L1 when drafting Run Contract from contribution plan.

**Curator:** **contribute** — mandatory ≥1 upvote in contract when qualified. **Explore** — recommend ≥1 upvote when merited; include in Run Contract when planned.

## Role Pick algorithm

```
1. Top gap recommended_action → L1 map
2. L3 micro-adjust (announcement → author; hotspot → commenter)
3. If saturation BLOCK and top=post → linker > commenter
4. If last 2 role_history same L1 → rotate tie-break
5. **Do not ask user to pick L1** — fold into Run Contract Phase 1.5; user may 修改 before 同意执行
```

_(Contribute: run after Phase 4 gap list. Explore emergent write: infer L1 from stroll gap when building contract.)_

## Downgrade rules (Deep Read)

If target thread already has substantive Chinese answer:

- author → linker or commenter (narrow sub-question)
- Still run curator on quality comments in thread when upvote planned

## Curator heuristics

Upvote candidates:

- Not own content; Chinese; ≥150 chars; executable detail (operator, region, tests)

Do not upvote:

- Empty praise, OP repeat, English-only fluff, marketing tone

Limits:

- Max 1 upvote per post per run
- Track `upvoted_comment_ids` in profile + ledger

## MCP by L1 (exact tool names, server: user-brain-api)

| L1 | Read MCP | Write MCP (after Run Contract 同意执行) |
|----|----------|-------------------------------------------|
| commenter | `read_full_forum_post` or `read_forum_post` | `create_forum_comment` |
| author | `search_*`, `read_full_forum_post` | `create_forum_post` |
| linker | `search_*`, `read_full_forum_post` | `create_forum_comment` (body含链接) |
| curator (when planned) | `read_full_forum_post`, `get_forum_comment_votes` | `upvote_forum_comment` |

Full phase map: [mcp-by-phase.md](mcp-by-phase.md).
