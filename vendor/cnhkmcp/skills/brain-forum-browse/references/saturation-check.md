# Saturation Check

Required when **session_l1=author** and planning `create_forum_post`.  
MCP only — no guessing duplicate titles.

## Procedure

```
1. title_keywords ← draft title + L2 tokens
2. MCP search (usually search_specific_forum_fast; slow if ambiguous)
3. MCP read_full_forum_post on hits where title_sim > 0.5
4. ≥2 posts with sim ≥ 0.65 → BLOCK_POST
5. 1 post sim ≥ 0.65 → WARN → commenter on that post
6. cluster ≥ 3 similar titles in 7d → BLOCK_POST, recommend linker
```

## Outcomes

| Result | Next step |
|--------|-----------|
| ALLOW | Proceed author draft |
| WARN | Auto: prefer **commenter** on existing post with narrow angle; document in Run Contract — **no user fork menu** |
| BLOCK_POST | Auto recommend linker; fallback commenter |

Log result in `forum_findings.md` and `session_plan.md` Phase 7.

## Not required for

- commenter / linker L1
- curator upvotes only runs
