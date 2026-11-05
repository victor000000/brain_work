# Gap Workflow

End-to-end gap scan after Official Scan + Live Registry.  
MCP map: [mcp-by-phase.md](mcp-by-phase.md) Phase 3–4.

## Steps

1. **MCP** `list_forum_posts_in_topic(topic_id=12913416465431)` + merge search hits / message links from Phase 2.
2. Filter `skip_registry` and hard exclusions locally (see gap-detection.md).
3. Classify gap_type per candidate (local).
4. **MCP** per L2 token: usually `search_specific_forum_fast`; add `slow` / `list_help_center_*` if needed.
5. Score with gap formula locally; sort descending.
6. Take top 5 for `forum_findings.md`; top 1 drives Role Pick.
7. If top gap repeats 2 runs without action → `low_roi_post_ids` (local).

## Output files

- `outputs/runs/<run_id>/gap_run_<ts>.json` — structured list
- `outputs/runs/<run_id>/gap_run_<ts>.md` — human summary
- Update `session_plan.md` Phase 4 ✓

## recommended_action mapping

| gap_type | recommended_action | session L1 |
|----------|-------------------|------------|
| UNANSWERED, UNDERSERVED, STALE_FAQ | comment | commenter |
| TOPIC_VOID, GLOSSARY_VOID | post | author |
| high dup cluster | link | linker |

See [role-matrix.md](role-matrix.md) for overrides.
