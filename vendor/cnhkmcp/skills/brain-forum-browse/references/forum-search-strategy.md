# Forum Search Strategy (MCP toolkit — pick by situation)

Agent **knows all search/discovery MCP tools below** and **chooses per step** — no fixed fast→slow pipeline every time.

Server: `user-brain-api`. Log chosen tools in `session_plan.md` MCP call log.

---

## Tool menu

| Tool | Mode | Scope | Speed | Best for |
|------|------|-------|-------|----------|
| `search_specific_forum_fast` | keyword | Single topic (default 中文论坛) | ~1s | Routine L2 token search, quick dedup, diversity check |
| `search_all_forum_slow` | keyword | Help Center HTML + cross-topic hydrate | ~20–40s | Sparse fast results, cross-locale, author saturation when fast unclear |
| `list_forum_posts_in_topic` | browse | All posts in one topic | ~1s | Live Registry, hot threads, no keyword yet |
| `list_forum_topics` | browse | Topic list | ~1s | Phase 2 discovery |
| `list_help_center_articles` | browse | Help Center articles | ~1s | GLOSSARY_VOID, official doc hunt |
| `get_help_center_article` | read | Single HC article | ~1s | After list HC |
| `get_glossary_terms` | seed | Glossary tokens | ~1s | L2 seed tokens (not Deep Read anchor) |

Hits are metadata only — follow with `read_full_forum_post` / `read_forum_post`.

---

## How to choose (agent discretion)

```
Need keyword in 中文论坛?     → usually search_specific_forum_fast first
Fast enough / rich results? → stop; read top hits
Fast sparse or still unsure?  → optionally search_all_forum_slow (same query)
Need browse without keyword?  → list_forum_posts_in_topic
Need glossary / HC doc?       → get_glossary_terms / list_help_center_articles
Combining multiple tools?     → merge by post_id; dedupe in findings
```

**Prefer fewer calls:** one well-chosen tool beats running every tool every phase.

---

## Suggested (not mandatory) use by phase

| Phase | Typical picks | Consider also when… |
|-------|---------------|---------------------|
| 2 Official Scan | `list_forum_topics`, `get_glossary_terms` | `list_help_center_articles` for themes |
| 3 Live Registry | `list_forum_posts_in_topic` | — |
| 4 Gap Scan | `search_specific_forum_fast` per L2 token | `slow` if fast `<3`; `list_help_center_*` if GLOSSARY_VOID |
| 7 Saturation (author) | `search_specific_forum_fast` on title | `slow` if fast ambiguous or author post |
| 8 Diversity | `search_specific_forum_fast` on draft keywords | `slow` if overlap risk high |
| linker index | `search_specific_forum_fast` on index title | `slow` to find cross-topic links |

---

## Quotas (soft caps)

See [quotas-and-cooldown.md](quotas-and-cooldown.md). `search_all_forum_slow` is **expensive** — use when justified, max 5/run.

---

## Examples

**Fast only (common):**
```json
{ "toolName": "search_specific_forum_fast",
  "arguments": { "search_query": "PPAC turnover", "topic_id": 12913416465431, "max_results": 15 } }
```

**Slow when fast sparse:**
```json
{ "toolName": "search_all_forum_slow",
  "arguments": { "search_query": "PPAC turnover", "locale": "zh-cn", "max_results": 10 } }
```

**Browse:**
```json
{ "toolName": "list_forum_posts_in_topic",
  "arguments": { "topic_id": 12913416465431, "max_results": 50 } }
```

---

## Anti-patterns

- **Only ever calling fast** and ignoring that `slow` / `list_*` / HC tools exist
- **Always calling slow** when fast already returned good hits (wastes quota/time)
- WebFetch / browser instead of any MCP search tool
- Declaring "no forum posts" without trying an alternative search method when first tool returned empty
