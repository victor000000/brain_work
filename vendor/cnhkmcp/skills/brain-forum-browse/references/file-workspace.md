# File Workspace

Cross-session disk memory lives in `outputs/workspace/`. Context = RAM; workspace = disk.

## Core files

| File | Purpose |
|------|---------|
| `action_ledger.json` | Full history: read/comment/post/upvote, angles, snippets |
| `skip_registry.json` | Pinned and low-ROI posts to exclude from gap candidates |
| `forum_memory.md` | Human-readable run summaries |
| `personal_experience_memory.md` | Hand-editable research habits (P1) |
| `external_memory_snapshot.json` | Phase 0a harvest from host AI memory |

Per-run snapshots go under `outputs/runs/<run_id>/`.

## Read before MCP

On every run:

1. Read workspace files (create via `scripts/init_workspace.py` if missing).
2. Copy templates into `outputs/runs/<run_id>/` for `session_plan.md`; **explore** → also `forum_stroll_notes.md`; **contribute/hybrid** → `forum_findings.md`.
3. **Then** call forum/platform MCP — never reverse this order.
4. **Never substitute MCP** with browser, WebFetch, or `brain-alpha-judge` static corpus for live forum state.

**Forum post content exists only after MCP returns** — local files cache summaries, not truth.

## Pinned post trap

Default skip `4902349883927` (glossary anchor).

Heuristics to add to `skip_registry.pinned_post_ids`:

- `vote_sum >= 50` and title matches `术语|必读|glossary|导航|Click here`
- Topic list top-3 with high comment_count but low gap_score → `pinned_low_roi`

Rules:

- `get_glossary_terms` → seed tokens only; never Deep Read glossary anchor as gap target.
- Filter `list_forum_posts_in_topic` through `skip_registry` before gap scoring.
- Same post_id in gap_list 2 runs without contribution → add to `low_roi_post_ids`.

## Ledger updates

| Event | Update |
|-------|--------|
| Deep Read complete | append `read_post_ids` |
| Comment/post/upvote success | append `contributed_*` + `past_contribution_snippets` |
| New pinned detected | append `pinned_marked` + `skip_registry` |

## already_read_penalty

In gap scoring: if `post_id in read_post_ids`, set `already_read_penalty = 1` (subtract 0.25 from score).

Hard exclude: `contributed_post_ids` unless STALE_FAQ with newer `updated_at` than ledger record.
