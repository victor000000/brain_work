# L3 Signal Patterns

Runtime-derived weights. No persistent registry file.

## Pattern rules

| Signal in scan text | L3 slug | L1 bias |
|---------------------|---------|---------|
| competition deadline / 截止 | deadline-responder | commenter, linker |
| Theme / pyramid / multiplier announcement | announcement-explainer | author |
| topic post_count spike | hotspot-commenter | commenter + curator upvote focus |
| new feature / API change | announcement-explainer | author |
| glossary / 术语 | glossary-responder | author or commenter |

## Application

1. Match patterns against `get_messages` + `get_events` + hot topic titles.
2. Emit `l3_signals[]` in manifest and scan JSON.
3. Role Pick: apply ±1 tie-break toward biased L1 (see role-matrix.md).
4. When signal absent next run, drop weight automatically.

## Cross-filter with L2

Only boost gaps whose tokens overlap user `l2[]` from profile. Example: PPAC user + Theme PPAC announcement → strong author bias on PPAC voids only.
