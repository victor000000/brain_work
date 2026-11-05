# Official Scan



Mandatory Phase 2 **in contribute/hybrid recon**.  

**Explore:** welcome purposeful signals from the same MCP batch (`get_messages`, `get_events`, pinned/topic listing) — **without** requiring formal gap scoring or scan JSON outputs upfront.



## Parallel MCP batch (fire all 4 together)



| Tool | Args |

|------|------|

| `get_messages` | `limit=30` |

| `get_events` | _(none)_ |

| `list_forum_topics` | `max_results=50` |



| `get_glossary_terms` | _(none)_ | **Default in batch** — L2 seed tokens only |



## Outputs



- `outputs/runs/<run_id>/scan_<ts>.json` — raw summaries + detected signals _(contribute/hybrid; explore optional)_

- Update `forum_findings.md` with announcements, pinned posts, hot topics

- New pinned → `skip_registry.json`



## Pin detection heuristics



- High votes + nav/glossary title patterns

- Known anchor `4902349883927`

- Official sticky patterns from topic listing



## L3 derivation



Pass scan text to [l3-signal-patterns.md](l3-signal-patterns.md); intersect with user L2 for search token weighting.  

Explore purposeful stroll: use L3 hints to **steer** browsing, not to force gap pipeline.

