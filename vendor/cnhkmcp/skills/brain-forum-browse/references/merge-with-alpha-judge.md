# Merge with brain-alpha-judge

## Boundaries

| Task | Skill |
|------|-------|
| Pre-submit alpha review | `brain-alpha-judge` — static `forum_corpus/`, no live forum |
| Browse forum, fill gaps, contribute | `brain-forum-browse` — **live MCP only** |
| Bake forum standards into judge | Manual: curate from MCP reads → update alpha-judge corpus |

## MCP-only rule

- **brain-forum-browse** **must** use MCP for all live forum/platform reads and writes.
- Judge static `forum_corpus/` is **style reference only** — never a substitute when MCP is available.
- If user runs **brain-forum-browse**, agent **defaults to MCP**; do not skip to corpus because it is faster.

## Allowed cross-use

- **brain-forum-browse** may **read** alpha-judge rubric / corpus examples to improve draft quality
- Judge must **not** call forum MCP during judge runs

## Evidence vs judge corpus

| Source | Role in forum writes |
|--------|----------------------|
| alpha-judge `forum_corpus/` | Style/rubric reference only — **not** E2 evidence for live claims |
| MCP `read_*` / `search_*` | E2 — required for forum-fact claims |
| `get_user_alphas` / P0–P5 memory | E1 — required for personal metric claims |

Forum writes use [evidence-and-review.md](evidence-and-review.md) (E1/E2/E3 + adversarial subagent). Judge corpus cannot substitute MCP reads or back unsupported claims in Run Contract drafts.

## Corpus path

Judge corpus: `untracked/skills/brain-alpha-judge/data/forum_corpus/`

Do not duplicate corpus into **brain-forum-browse**. Discovery flow:

```
brain-forum-browse live MCP read → human curate → add markdown to judge corpus + index.json
```
