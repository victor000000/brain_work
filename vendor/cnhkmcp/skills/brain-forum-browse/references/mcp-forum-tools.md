# MCP Forum Tools

**Default: all BRAIN platform + forum operations go through MCP.**  
Use this list directly. Do not list/discover MCP tools at runtime. Do not use browser, WebFetch, or static corpus as live forum data.

**Phase workflow map:** [mcp-by-phase.md](mcp-by-phase.md)

## Server

| Host | How to call |
|------|-------------|
| Cursor Agent | `CallMcpTool` → `server: "user-brain-api"`, `toolName: "<name below>"` |
| Cursor (legacy) | `mcp_brain-api_<name>` e.g. `mcp_brain-api_search_specific_forum_fast` |
| Claude Code | MCP server `user-brain-api`, tool name as below |

Deploy path: `D:/BRAINProject/BRAINMCP_pythonserver/platform_functions.py`  
Default Chinese forum: `topic_id = 12913416465431` (`CHINESE_FORUM_TOPIC_ID`)

## Auth

- `email` / `password` optional on forum tools if server `user_config.json` is configured.
- Never read or commit credential files from the repo.

---

## Tools this skill uses (exact names)

### Official Scan & registry (read)

| Tool | Required args | Default / tips |
|------|---------------|----------------|
| `get_messages` | — | `limit=30` for Phase 2 |
| `get_events` | — | L3 signal source |
| `list_forum_topics` | — | `max_results=50` |
| `get_glossary_terms` | — | L2 seed tokens only; do not Deep Read glossary anchor post |
| `list_forum_posts_in_topic` | `topic_id` | use `12913416465431`; filter skip_registry before gap scoring |

### Search & discovery (pick by situation)

Full menu: [forum-search-strategy.md](forum-search-strategy.md). Agent chooses — **not every run needs slow**.

| Tool | Required args | When |
|------|---------------|------|
| `search_specific_forum_fast` | `search_query`, `topic_id` | Default keyword search in 中文论坛 |
| `search_all_forum_slow` | `search_query`, `locale=zh-cn` | When fast sparse or broader coverage needed |
| `list_forum_posts_in_topic` | `topic_id=12913416465431` | Browse topic without keyword |
| `list_forum_topics` | `max_results` | Phase 2 |
| `list_help_center_articles` | `max_results` | GLOSSARY_VOID / HC hunt |
| `get_help_center_article` | `article_id` | Read HC article |

### Read posts (after search)

| Tool | Required args | When |
|------|---------------|------|
| `read_forum_post` | `article_id` | Preview / short posts |
| `read_full_forum_post` | `article_id` | Deep Read, comment threads, curator |

### Personal context (read, optional Phase 0b)

| Tool | Required args | When |
|------|---------------|------|
| `get_user_alphas` | — | P5 facts for Perspective Card |
| `get_user_profile` | — | optional `user_id="self"` |

### Curator (read before write)

| Tool | Required args | When |
|------|---------------|------|
| `get_forum_comment_votes` | `post_id`, `comment_id` | Verify vote count before suggesting upvote |

### Write (**user confirm each call**)

| Tool | Required args | L1 |
|------|---------------|-----|
| `create_forum_comment` | `post_id`, `body` (**HTML**, not Markdown) | commenter, linker |
| `create_forum_post` | `topic_id`, `title` (plain text), `details` (**HTML**) | author |
| `upvote_forum_comment` | `post_id`, `comment_id` | curator (all users) |

---

## Tools installed but NOT for this skill

Do not call unless the user explicitly requests:

- `delete_forum_comment`, `delete_forum_vote` — destructive
- `create_simulation`, `create_multi_simulation`, `get_datasets`, `get_datafields`, `get_operators`, `check_correlation`, `get_submission_check`, … — alpha research, not forum

---

## Phase → tool cheat sheet

```
Phase 2 Official Scan:
  get_messages(limit=30) + get_events() + list_forum_topics(max_results=50)

Phase 3 Live Registry:
  list_forum_posts_in_topic(topic_id=12913416465431)

Phase 4 Gap Scan (per L2 token):
  search_specific_forum_fast(...) — add search_all_forum_slow or list_* if needed

Phase 7 Saturation (author):
  search_specific_forum_fast on title; slow optional

Phase 8 Diversity:
  search_* from toolkit + read top hits

Phase 9 Act (after confirm):
  create_forum_comment | create_forum_post | upvote_forum_comment
```

## Example calls (Cursor CallMcpTool)

```json
{ "server": "user-brain-api", "toolName": "search_specific_forum_fast",
  "arguments": { "search_query": "PPAC turnover", "topic_id": 12913416465431, "max_results": 15 } }

{ "server": "user-brain-api", "toolName": "search_all_forum_slow",
  "arguments": { "search_query": "PPAC turnover", "locale": "zh-cn", "max_results": 10 } }

{ "server": "user-brain-api", "toolName": "list_forum_posts_in_topic",
  "arguments": { "topic_id": 12913416465431, "max_results": 50 } }

{ "server": "user-brain-api", "toolName": "create_forum_comment",
  "arguments": { "post_id": "32984819083415", "body": "…简体中文…" } }
```

## Fallback policy

| Situation | Action |
|-----------|--------|
| First keyword search returned empty/sparse | try `search_all_forum_slow` or `list_forum_posts_in_topic` |
| `read_full_forum_post` fails | try `read_forum_post` once |
| Any write tool missing | log in session_plan; skip write; **never browser** |
| MCP server down / auth fail | **stop run**; ask user to fix MCP — no offline improvisation |

## Verify deployment

Tool names must match `user-brain-api` MCP descriptors and `platform_functions.py` `@mcp.tool()` registrations.
