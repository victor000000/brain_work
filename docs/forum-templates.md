# Templates mined from the BRAIN community forum

> Historical reference retained from the 2026 source snapshot. Counts, availability, thresholds and economic explanations below are dated observations or source claims, not current platform guarantees. For current admission and verification use [Research](RESEARCH.md); refresh native metadata/verdicts before spending quota. Raw corpora and account evidence are deployment-local and omitted from publication.
Harvested 2026-10-02 over plain HTTP (no browser) — see `TODO.md` for the
access method. Verified faithful against a post supplied as ground truth:
body text, vote counts (55 / 1 / 21) and comment ordering all matched exactly.

**Corpus: 8,245 posts + 91,213 comments = 99,349 documents.**

Raw data (`tools/spider_forum.py` regenerates the two large dumps):
- `docs/forum/forum_posts.json` — post index
- `docs/forum/forum_bodies.json` — post HTML (gitignored, 48 MB)
- `docs/forum/forum_comments.json` — comments (gitignored, 82 MB)
- `docs/forum/forum_templates.json` — mined output

## Mining result

| | |
|---|---|
| Distinct templates | **11,438** |
| Fillable from pv/option | **10,228** |
| Need data outside the restriction | 1,210 |
| Expressions found in posts | 19,241 |
| Expressions found in comments | 6,692 |

**5,065 templates (44%) appear only in comments.** A posts-only pass — which is
what the first extraction did — sees less than half the corpus. 460 templates
appear in both.

`★` Comments are where the discussion happens. The posts announce results;
the comments explain method, argue about operator semantics, and correct each
other. Mining posts alone would have missed nearly half of everything here.

## Concrete pv/option-native templates

| Template | Idea |
|---|---|
| `(close - ts_mean(close, 20)) / ts_stddev(close, 20)` | Classic 20d price z-score |
| `1.0/ts_std_dev(stats.returns, 250)` | Inverse trailing volatility |
| `ts_delta(close, 1)` / `ts_mean(close, 5)` | Return and moving average primitives |
| `ret_co = open/ts_delay(close, 1) - 1` | Overnight gap return |
| `my_group2 = bucket(rank(cap), range='0,1,0.1')` | Cap deciles as a custom grouping |
| `group_neutralize(alpha, bucket(rank(cap), range="0.1,1,0.1"))` | Neutralise within cap deciles |
| `trade_when(rank(volume/adv20) > 0.5, pcr_oi_all, -1)` | Trade options put/call OI only on above-average volume — **pv + option together** |
| `trade_when(volume > adv20, group_neutralize(alpha, my_group2), -1)` | Volume-gated, cap-decile-neutral |
| `min(group_rank(X, sector), rank(ts_delta(X, 66)))` | Intersection of cross-sectional and time-series strength |

## Pattern templates (slots to fill)

| Pattern | Role |
|---|---|
| `data = winsorize(ts_backfill(<data>, 63), std=4.0)` | Standard cleaning step |
| `group_zscore = (x - group_mean(x, group)) / group_stddev(x, group)` | Manual group z-score |
| `ic = if_else(innerCorr == 1.0, nan, innerCorr)` | Degenerate-correlation guard |
| `trade_when(squeeze_regime, main_signal, -1)` | Regime-gated signal |
| `group_neutralize(signal, industry)` | Industry neutralisation |

The cleaning pattern `winsorize(ts_backfill(<data>, 63), std=4.0)` appears
verbatim in the forum corpus **and** in cnhkmcp's template documentation —
two independent sources converging on the same constants.

## Classification caveat

Field classification uses the pruned DB: a token is pv/option if it appears in
`data_fields`, and non-pv if it carries a dataset prefix (`mdl216_*`, `anl14_*`)
whose dataset is not in the pv/option set. **Unprefixed non-pv names** (`assets`,
`sales`) can no longer be resolved — that reference was deleted by the DB prune —
so they are skipped rather than guessed, and a template mentioning them is
neither confirmed nor rejected.

The extraction is also heuristic: a few prose fragments leak through when a
sentence contains an operator call (e.g. *"On the other hand, ts_co_kurtosis(x,
y, n) seems to measure..."*). These are noise in the low-frequency tail, not in
the ranked head.

## Re-crawled 2026-10-09: still saturated, and now measured by comment count

A fourth refresh (`tools/spider_forum.py --index`, then `--bodies --comments`)
found the same corpus as 2026-10-08 and produced the same mined output:
**9,767 skeletons and 1,268 fillable before and after, 0 added, 0 removed.**

The index is the useful part this time, because it carries `comment_count`.
Comparing the platform's own count against the previous crawl's index says the
forum gained **nothing**: exactly one post's comment count moved (27 → 24, three
comments deleted), and 631 posts whose `updated_at` moved carried no comment
change at all — Zendesk moves `updated_at` on edits and topic maintenance. That
is a cheaper and more direct check than the spider's re-queue, which on the
2026-10-08 run had looked like 1,624 posts of new material and was not.

The refresh also cost 21.8 minutes and 95 empty bodies re-fetched (1 failure).
**Fresh logins are CAPTCHA-gated under load**: with twelve workers
re-authenticating on 401, `POST /authentication` starts answering
`400 {"captcha":["This field is required."]}`, and every session rebuilt from
one then 401s on content. A single-threaded login immediately afterwards
succeeds. Anything that spawns its own workers needs to serialise its auth.

## The help centre: a second Zendesk corpus (harvested 2026-10-09)

The forum miner walks community topics only. The help centre —
`support.worldquantbrain.com/hc/en-us/articles`, 602 articles in 90 sections —
is a separate corpus that nothing in the tree read, and it needs no new client:
the list endpoint returns each article's rendered body, so the whole corpus is
seven requests.

**It is thin, and the mining result says so:**

| | |
|---|---|
| Articles | 602 |
| Expression-shaped lines | 59 |
| Distinct skeletons | 55 |
| Fillable from pv/option | 11 |
| Rejected — foreign fields | 44 |
| Fillable but already elsewhere | 10 |
| New usable in the loaded pool | **1** (`rank({f}) + rank({f})`) |

Rows live in `docs/forum/help_center_templates.json`, bodies in
`help_center_articles.json`; only `en-us` exists (zh-cn / zh-tw / ja / ko each
return 0 articles). The loaded pool went from 572 to 573 usable skeletons.

## 1,926 shapes sit behind the per-skeleton fillable flag (measured 2026-10-09)

The corpus marks `fillable_from_pv_option` **per skeleton**: one line that uses
a fundamental field disqualifies the shape, even when other lines producing it
are pv-native. `rank({f}) + rank({f})` is the case in point — it is in the
forum corpus with the flag *false* (a source line used `book_to_price` and
`earnings_yield`) and in the help-centre corpus with the flag *true*.

Measured against `generator.template_fill.is_usable` — the gate that would
reject any skeleton whose literal tokens are not pv/option fields — **1,926
rows currently flagged false are shapes the generator would accept**: 599
single-call forms (`rank({f})`, `ts_delta({f},1)`), 1,327 multi-call, 743 of
those with two or more slots. Recomputing the flag with the generator's own
gate would raise the pool from 573 to roughly 2,500.

**Not done.** The gate itself would not be weakened — that is what the count
above is measured with — but the pool would grow 4.4x on shapes of very uneven
quality, and the mixed ones are exactly the near-duplicates of the built-ins
(`subtract({f},{f})`, `max({f},{f})`) the loader was tightened against. It is a
corpus-policy decision with a quality tradeoff, not a bug fix, so it is
recorded here rather than taken.

## Not usable under the pv/option restriction

1,210 templates reference fields outside price/options — analyst estimates
(`anl14_*`), fundamentals (`fnd*`), news (`nws*`, `news_*`), models (`mdl*`),
sentiment (`scl*`), earnings (`ern*`). They stay in `forum_templates.json`
flagged `fillable_from_pv_option: false`, so they can be revisited if the
restriction ever widens.
