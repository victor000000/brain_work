# Quotas and Cooldown

Per-run limits (write-enabled default). Config: [config.example.json](../configs/config.example.json).

| Resource | Max/run |
|----------|---------|
| search_specific_forum_fast | 30 |
| search_all_forum_slow | 5 |
| list_forum_posts_in_topic | 3 |
| list_help_center_articles | 2 |
| get_help_center_article | 5 |
| read_forum_post / read_full_forum_post | 8 combined |
| create_forum_comment | 3 |
| create_forum_post | 1 |
| upvote_forum_comment | 3 |

## Search policy

- Multiple MCP search tools available — agent **chooses by situation** ([forum-search-strategy.md](forum-search-strategy.md)).
- `search_all_forum_slow` is expensive; use when fast insufficient, not every query.
- Track counts in session_plan MCP call log.

## Policy

- Prefer **comment over post**
- Max **3 write actions** total in plan (comments + posts + upvotes combined display; upvotes count toward curator minimum suggestion, not always executed)

## Cooldown (soft)

- Do not comment same post_id twice in consecutive runs unless new official info
- Do not repost same angle_slug within 5 runs (see content-diversity.md)
- Upvote: skip if comment_id already in `upvoted_comment_ids`

## Rate discipline

Batch reads; avoid redundant search with identical query strings in one run.

**Track in session_plan «MCP call log»** — increment after each tool invocation. Stop at quota; do not substitute browser or manual URL fetch.
