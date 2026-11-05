# Content Diversity

Align official direction; differ in angle. Prevents 100 agents posting the same Sharpe tips.

**Evidence gate (hard):** Diversity does not excuse unsupported claims. All draft claims must pass [evidence-and-review.md](evidence-and-review.md) (E1/E2/E3 + adversarial review) **before** Run Contract.

## Dual track

| Track | Do | Don't |
|-------|-----|-------|
| Align | Read official asks from messages/events | Parrot announcements |
| Differ | L2 + fresh angle_slug + personal memory | Repeat community structure or own past snippets |

## Angle pool

Track in `action_ledger.content_angles_used[]`:

| angle_slug | Example |
|------------|---------|
| ppac-turnover-operator | ts_target_tvr 实操 |
| ppac-submission-debug | 提交测试踩坑 |
| ppac-region-usa | USA 区域特化 |
| vf-diversity-atom | VF 与单 dataset |
| beginner-first-template | 新手第一模板 |
| theme-official-interpret | Theme 中文解读 |
| theme-counterexample | Theme 失败案例 |
| dataset-field-audit | dataset 字段审计 |

Pick angle_slug **not used in last 5 runs**. If exhausted → change topic or L1=linker.

## Community Similarity Check

After Saturation, before Draft — **MCP read, no writes**:

```
1. MCP search_specific_forum_fast(keywords + L2, ...) — or other toolkit tool if better fit
2. MCP read_full_forum_post on top hits + target post
3. claims[] from MCP text; overlap vs draft_claims; diversity_ok = community_ok AND personal_ok
```

On fail: commenter → sub-argument; author → new angle/title or linker; log overlap in findings.

## Banned patterns

- Generic titles after Theme: `【Theme分享】`, `提高 Sharpe 的几点心得` (no dataset/region/operator)
- Same 【】 template as top-3 search results in 7 days
- Comments that only agree with OP — need ≥1 new executable detail
- **Empty praise** — 「感谢分享」「学到了」「+1」as entire comment
- **Parroting** — same steps/metrics as OP or top comment without your E1/E1-chat/P5 data
- Re-posting generic Sharpe/turnover tips without your angle — see [unique-contribution.md](unique-contribution.md)

## Official appeal response (L3 announcement/competition)

```
official_points[] ← MCP get_messages (Phase 2 scan JSON)
covered_points[] ← MCP keyword search (toolkit) + read_full_forum_post on top hits
uncovered = official_points - covered_points
Draft only uncovered; title must include L2 + region/dataset/operator
If fully covered → linker (create_forum_comment) or commenter on best existing thread
```

## Gap score diversity boost (optional)

```
diversity_boost = 1.0 if similar title cluster < 2
                = 0.5 if cluster == 2
                = 0.0 if cluster >= 3
gap_score_final = gap_score * (0.85 + 0.15 * diversity_boost)
```
