# Personal Perspective

Combine skill memory + host external memory + **MCP P5** for unique forum voice.

## Phase 0b MCP (P5) — default every run

| Tool | When |
|------|------|
| `get_user_alphas` | **Default** — extract verifiable alpha/dataset patterns for Perspective Card |
| `get_user_profile` | Optional `user_id="self"` |

Tag facts as `[brain_mcp]`. MCP fail → omit P5 facts; **never invent** metrics.

## Perspective Card (required before Draft)

Write to `forum_findings.md`:

```markdown
## Perspective Card
- memory_sources: [skill_local, claude_md, cursor_rules, brain_mcp, session]
- L2: ...
- angle_slug: ...
- 个人独特点（≥2 条，标注来源）:
  1. [skill_local] ...
  2. [CLAUDE.md] ...
- 社区已覆盖: ...
- 本人过往已说过（P0）: ...
- 本轮新信息: ...
```

## Personal Uniqueness Check

```
self_claims[] ← merge(P1, external_memory_snapshot.merged_bullets, P5 MCP)
past_claims[] ← action_ledger.past_contribution_snippets (last 10)
self_overlap = |self_claims ∩ past_claims| / |self_claims|
personal_ok = self_overlap < 0.4
  AND ≥1 self_claim not in community_claims
  AND ≥1 self_claim not in past_claims
diversity_ok = community_ok AND personal_ok
```

On failure: swap angle_slug, pick unused 踩坑 from memory, or change target post.

## After Act

1. Extract 1–2 claim summaries → `past_contribution_snippets`
2. Propose new reusable tips → `personal_experience_memory.md` (user may delete)
3. Append to `forum_memory.md`: 本轮独特视角 + 与社区差异

## Forbidden

- Fabricate VF, rank, submission counts not in memory/MCP
- Copy-paste past snippets verbatim
- Generic forum filler ignoring P1/P2
