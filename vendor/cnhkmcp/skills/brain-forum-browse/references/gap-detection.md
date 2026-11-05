# Gap Detection

## Gap types

| Type | Trigger | Default action |
|------|---------|----------------|
| UNANSWERED_THREAD | comment_count=0 + question shape | comment |
| UNDERSERVED_THREAD | vote_sum≥5, comment_count≤2 | comment |
| TOPIC_VOID | bucket search_scarcity≥0.7 | post (saturation) |
| GLOSSARY_VOID | term zero results | post |
| STALE_FAQ | >180d stale, few comments | comment |

## Scoring formula

```
gap_score = 0.35*search_scarcity + 0.30*engagement_gap + 0.15*recency_boost
          + 0.20*quality_void - 0.40*dup_penalty - 0.25*already_read_penalty
```

- `already_read_penalty = 1` if post_id ∈ `read_post_ids`, else 0
- Admission: `gap_score >= 0.45` (config `gap_threshold`)

## Exclusions

- Hard: `skip_registry.pinned_post_ids`, `contributed_post_ids` (except STALE_FAQ with newer update)
- Soft: read posts get penalty

## search_scarcity

From L2 bucket tokens in `configs/topic-buckets.yaml`:

- **MCP** per token — agent picks from [forum-search-strategy.md](forum-search-strategy.md):
  - usual: `search_specific_forum_fast`
  - if sparse: `search_all_forum_slow` or `list_forum_posts_in_topic`
- scarcity = 1 - min(1, result_count / 10)

## dup_penalty

High if title similar to recent posts (≥0.65) or same gap type already contributed this week.
