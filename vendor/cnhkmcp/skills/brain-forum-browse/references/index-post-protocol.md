# Index Post Protocol (optional)

For users with `index_protocol_opt_in: true` in profile. Typically **linker** L1.

## Format

**Title:** `【社区索引】{L2} · {YYYY-MM}`

**Body:**

- Short intro (why this index exists)
- Bulleted links to 3–8 quality threads with one-line description each
- HTML comment marker for future parsers (optional):

```html
<!-- brain-forum-index:l2=PPAC;updated=2026-06-05 -->
```

## Rules

- **MCP first:** search toolkit — usually `search_specific_forum_fast` for `【社区索引】{L2}`
- Update existing index via **`create_forum_comment`** on that post if same month + L2
- New index via **`create_forum_post`** `(topic_id=12913416465431)` only if none exists
- Do not duplicate saturation-blocked topic — linker merges into existing index post
- Chinese only

Body must be **HTML** (links as `<a href>`). See [write-style-zh.md](write-style-zh.md).

## Saturation

Index posts still run Community Similarity; must add **new links** not in last index revision.
