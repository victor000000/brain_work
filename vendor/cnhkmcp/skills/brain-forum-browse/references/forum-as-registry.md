# Forum as Registry

No remote JSON registry. **Live forum content = MCP reads only** (`user-brain-api`).

## Dedup before post (MCP)

```
search_specific_forum_fast(title_keywords + L2 tokens, topic_id=12913416465431)
→ optionally search_all_forum_slow if fast sparse
→ read_full_forum_post on hits; if title_sim >= 0.65 → comment/linker not new post
```

## Coordination at scale

- L2 partitions search space
- Gap scoring spreads users across threads
- angle_slug rotation + Community Similarity prevents duplicate essays
- linkers maintain index posts (optional protocol)

## Live Registry phase

**MCP:** `list_forum_posts_in_topic(topic_id=12913416465431, max_results=50)`

Then locally:

- Filter `skip_registry`
- Deprioritize ledger `read_post_ids` / `contributed_post_ids` unless STALE_FAQ refresh
- Feed candidates to Gap Scan

Per-run `forum_manifest.json` captures gap_list, session_l1, actions — not a global registry.
