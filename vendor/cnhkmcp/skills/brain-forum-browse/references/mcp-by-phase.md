# MCP by Phase



**Default policy: 平台 + 论坛 = 全部 MCP.** Server: `user-brain-api`.  

Do not list tools at runtime — call names below directly.  

If MCP fails → stop and report; **no browser / no static corpus fallback**.



Cross-ref: [mcp-forum-tools.md](mcp-forum-tools.md) for args, examples, fallbacks.



---



## Phase 0 — Load Workspace



**No forum MCP.** Read local files only:



- `outputs/workspace/action_ledger.json`, `skip_registry.json`, `forum_memory.md`, `personal_experience_memory.md`

- Create run: `python scripts/init_workspace.py --new-run`



---



## Phase 0a — External Memory Harvest



**No forum MCP.** Read host project files → `external_memory_snapshot.json`.  

Optional script: `python scripts/harvest_external_memory.py --write`



---



## Phase 0b — Personal Context Sync (**default MCP**)



| Tool | Args | Purpose |

|------|------|---------|

| `get_user_alphas` | `limit=20` | **Run every session** — P5 facts for Perspective Card |

| `get_user_profile` | `user_id="self"` | optional extra context |



Skip only if MCP auth fails; log reason in session_plan — do not fabricate alpha facts.



---



## Phase 1 — Profile



**No forum MCP.** Read `data/agent_profile.json`; run `init_profile.py` if missing.



---



## Explore mode (stroll-with-mandatory-contribution) — **default for 「逛一逛论坛」**



When `run_mode=explore` (default per [run-modes.md](run-modes.md)):



| Phase | Action |

|-------|--------|

| 0 → 0a → 0b → 1 | Same as above — load workspace, optional harvest, `get_user_alphas`, profile |

| Purposeful inputs (when relevant) | `get_messages`, `get_events`, pinned/topic listing, memory-driven `search_*`, `read_*` — **agent picks by interest or starting intent** |

| Emergent browsing | Same MCP toolkit without fixed agenda; record **contribution plan** in stroll notes after finds |

| Deliverable | Write `outputs/runs/<run_id>/forum_stroll_notes.md` (template: [forum_stroll_notes.md](../templates/forum_stroll_notes.md)) — **contribution plan required** |

| Phase 7.5 | **Standard path** — adversarial review. **Skipped** if [auto-send-e1.md](auto-send-e1.md) A1–A8 pass |

| Phase 1.5 | **Standard path** — Run Contract → **同意执行**. **Skipped** for qualified auto-send E1 |

| Phase 6–9 | Execute — auto-send: after certification; standard: after **同意执行** |

| Chat report | Summarize stroll findings + contribution outcome; **no post-browse action menu** |



**Minimum contribution bar (explore):** ≥1 evidence-backed write (comment OR post) OR user-approved comment+upvote plan; recommend ≥1 E1/E2/E3 comment + consider curator upvote when merited. If nothing strong to say → linker-style minimal value; document why in stroll notes — **no empty sessions**.



**Skip in explore:** upfront formal gap scoring (Phases 2–5 as full contribute recon), mandatory Role Pick upfront.



**Do not skip:** MCP for platform/forum facts; mandatory contribution; Phase 6–9 execute. **May skip 7.5 + 1.5** only per [auto-send-e1.md](auto-send-e1.md).



If user later asks for gap-driven contribute in same session → full Recon (Phases 2–5) optional unless user wants contribute strictness.



---



## Contribute / hybrid recon — Phases 2–5



**Apply when `run_mode=contribute` or hybrid recon before writes.** Explore may use lighter parallel reads and purposeful scan signals without formal gap outputs.



## Phase 2 — Official Scan



**Call in parallel (4 reads — all default):**



| Tool | Args |

|------|------|

| `get_messages` | `limit=30` |

| `get_events` | _(none)_ |

| `list_forum_topics` | `max_results=50` |

| `get_glossary_terms` | _(none)_ — L2 seed tokens; not Deep Read target |



Write: `outputs/runs/<run_id>/scan_<ts>.json`, update findings + skip_registry for pinned posts.



See [official-scan.md](official-scan.md).



---



## Phase 3 — Live Registry



| Tool | Args |

|------|------|

| `list_forum_posts_in_topic` | `topic_id=12913416465431`, `max_results=50` |



Then **filter locally**: `skip_registry`, `action_ledger.read_post_ids` / `contributed_post_ids`.



See [forum-as-registry.md](forum-as-registry.md).



---



## Phase 4 — Gap Scan



Per [forum-search-strategy.md](forum-search-strategy.md) — **agent picks tools**:



| Typical | Tool | When |

|---------|------|------|

| Default | `search_specific_forum_fast` | per L2 token |

| Optional | `search_all_forum_slow` | fast sparse / void gap |

| Optional | `list_help_center_articles`, `get_help_center_article` | GLOSSARY_VOID |

| Optional | merge by `post_id` if multiple searches used |



Score locally per [gap-detection.md](gap-detection.md).



---



## Phase 5 — Role Pick



**No MCP.** Logic only → write `session_l1` to session_plan. See [role-matrix.md](role-matrix.md).



---



## Phase 1.5 — Run Contract (**STOP**)



When **any** planned write (contribute recon **or** explore stroll — **every explore session**):



1. Merge P0–P5 memory + (contribute: gap_list + session_l1; explore: stroll gap summary) → full auto plan

2. Write `outputs/runs/<run_id>/run_contract.md` (template: [run_contract.md](../templates/run_contract.md))

3. Present in chat: 搜帖 / 深读 / 跟评 / 点赞 / 新帖 + **完整中文草稿**

4. Wait **`同意执行`** | **`修改：…`** | **`取消`**

5. **Forbidden:**「你想先做哪一项？」菜单



See [run-contract.md](run-contract.md).



---



## Phase 6 — Deep Read (Execute block)



For each gap target post (quota: 8 reads/run combined):



| Priority | Tool | Args |

|----------|------|------|

| 1 | `read_full_forum_post` | `article_id=<post_id>` |

| 2 | `read_forum_post` | `article_id=<post_id>` if full fails |



Curator pass on same reads (when upvote planned in contract):



| Tool | Args |

|------|------|

| `get_forum_comment_votes` | `post_id`, `comment_id` for candidate upvotes |



Append `read_post_ids` to ledger after each read.



---



## Phase 7.5 — Evidence + Adversarial Review (**mandatory per draft**)

**Mandatory every session** (explore stroll and contribute) — **before** Phase 1.5 Run Contract presentation.

**No MCP writes.** May use MCP **read** to verify or fetch missing evidence.

### Per comment/post draft

1. Main agent drafts with inline `[E1/E2/E3: …]` tags + `evidence_sources[]`
2. Launch subagent via `Task` (`subagent_type: generalPurpose` or `explore`) with draft + evidence + MCP excerpts
3. **Cursor multitask mode:** `run_in_background=true` when reviewing multiple drafts in parallel
4. Subagent returns `PASS` | `REVISE` with specific issues (unsupported claims, fabricated numbers, overgeneralization, missing paper citation, tone)
5. Main agent revises or drops claims; **re-review** if major changes
6. Only `adversarial_review_status: pass` drafts proceed to Run Contract

See [evidence-and-review.md](evidence-and-review.md).

**Order:** Phase 7 (saturation, author) → **Phase 7.5** → Phase 8 (diversity) → Phase 1.5 Run Contract (if not yet presented) or update contract drafts.

---

## Phase 7 — Saturation Check (author only)



| Step | Tool |

|------|------|

| Dedup search | `search_specific_forum_fast` (usual); `search_all_forum_slow` if needed |

| Inspect hits | `read_full_forum_post` or `read_forum_post` when title_sim > 0.5 |



Outcomes: ALLOW / WARN / BLOCK_POST — see [saturation-check.md](saturation-check.md).



---



## Phase 8 — Draft + Diversity Check



**Every explore and contribute session.** Drafts must have **passed Phase 7.5** before inclusion in Phase 1.5 Run Contract — **no second per-item confirm here.**

If diversity adjustments change factual claims → re-run Phase 7.5 adversarial review on affected drafts.



**Read MCP only (no writes):**



| Step | Tool |

|------|------|

| Community Similarity | `search_*` (toolkit) + `read_*` on top hits |

| Target thread | `read_full_forum_post` on gap post if not read in Phase 6 |

| Official appeal | scan JSON + keyword search as needed for `covered_points` |



Run diversity checks per [content-diversity.md](content-diversity.md). Adjust drafts in Run Contract if needed; do **not** re-prompt user item-by-item.



See [write-style-zh.md](write-style-zh.md).



---



## Phase 9 — Act + Report



**Only after Run Contract `同意执行` (Phase 1.5), or auto-send E1 certification.** Then execute writes — no per-comment/post/upvote prompts.

**Before each write:** convert draft Markdown → **forum HTML** per [write-style-zh.md](write-style-zh.md). Never pass raw Markdown to MCP.

| Action | Tool | Required args |
|--------|------|---------------|
| Comment / linker reply | `create_forum_comment` | `post_id`, `body` (zh-CN **HTML**) |
| New post | `create_forum_post` | `topic_id=12913416465431`, `title` (plain text), `details` (**HTML**) |
| Curator upvote | `upvote_forum_comment` | `post_id`, `comment_id` |



Then update local files: ledger, `forum_memory.md`, `agent_profile.role_history`.

**Follow-on impulses (optional):** After writes complete, finalize 0–3 research/exploration proposals in stroll notes or findings — not in Run Contract; do not auto-invoke other skills. See [follow-on-impulses.md](follow-on-impulses.md).



---



## Decision tree (when stuck)



```

Need official / Theme / competition text?  → get_messages, get_events

Need post list in 中文论坛?                 → list_forum_posts_in_topic(12913416465431)

Need find posts by keyword?                → search_specific_forum_fast (try slow if sparse)

Need browse topic without keyword?         → list_forum_posts_in_topic

Need HC / glossary docs?                   → list_help_center_articles, get_help_center_article

Need post body + comments?                 → read_full_forum_post(article_id)

Need to comment?                           → create_forum_comment (after Run Contract 同意执行)

Need new thread?                           → create_forum_post (after confirm + saturation)

Need to upvote?                            → upvote_forum_comment (after confirm)

Auth error?                                → retry once; ask user; **stop** (no browser)

MCP server missing?                        → stop; tell user to enable user-brain-api

Tempted to use alpha-judge corpus as live? → **forbidden**; must use MCP read/search

```



Track call counts in session_plan Notes vs [quotas-and-cooldown.md](quotas-and-cooldown.md).

