# Complete Template Catalog

This document catalogs all templates available in the brain_work generator system, including their sources, performance characteristics, and field requirements.

> **Reconciled 2026-10-15.** The tables below were written when the website
> registry (§2) held 20 templates; it holds **38** today, and the 18 names
> the table predates are listed at the end of §2. The forum corpus (§3) has
> grown since: **9,797** skeletons, **1,277** fillable, from 99,666
> documents (8,329 posts + 91,337 comments). Rows are kept as written (their rationale still holds);
> the counts in the headings and the footer are current.

## Template Sources

### 1. cnhkmcp Templates (10 templates)
High-performing curated templates from cnhkmcp package plus canonical patterns.

**File**: `generator/templates_cnhkmcp.py`

| Template | Operators | Performance | Source |
|----------|-----------|-------------|--------|
| power_ratio | rank, signed_power | IS sharpe: -0.03 | cnhkmcp highperf |
| raw_regression_long | rank, ts_regression | IS sharpe: -0.10, generates +0.76 pattern | cnhkmcp highperf |
| raw_regression_medium | rank, ts_regression | IS sharpe: -0.09 | cnhkmcp highperf |
| staleness_decay | rank, days_from_last_change | IS sharpe: -0.07, +0.08 with 3f_mean | cnhkmcp vec |
| scale_rank_zscore | rank, scale, ts_zscore | IS sharpe: -0.08 | cnhkmcp advanced |
| quantile_ts_rank | quantile, ts_rank | exploration | cnhkmcp 3.1.11 canonical |
| group_rank_diff | group_rank | exploration | cnhkmcp 3.1.11 canonical |
| ts_corr_long | ts_corr, ts_backfill | exploration | cnhkmcp 3.1.11 canonical |
| trade_when_event | trade_when, days_from_last_change, rank | exploration | cnhkmcp 3.1.11 canonical |
| ts_backfill_negmean | ts_mean, ts_backfill | exploration | cnhkmcp 3.1.11 canonical |

### 2. BRAIN Website Templates (38 templates; 20 cataloged below)
Extracted from BRAIN forum, learn docs, and documentation. **PV and options fields only**.

**File**: `generator/templates_brain_website.py`

| Template | Category | Operators | Rationale |
|----------|----------|-----------|-----------|
| price_zscore_20d | momentum | ts_mean, ts_stddev | Price deviations from 20d mean revert |
| inverse_volatility | risk | ts_std_dev | Low volatility anomaly |
| overnight_gap | microstructure | ts_delay | Overnight gaps reverse intraday |
| volume_surge | volume | rank | Abnormal volume precedes price moves |
| capm_residual | risk_adjusted | ts_regression, group_mean, log, ts_mean | Isolates idiosyncratic alpha |
| price_momentum_xsec_ts | momentum | group_rank, rank, ts_delta, min | Intersection of cross-section & time-series strength |
| return_mean_reversion | mean_reversion | ts_mean, ts_delay | Short-term returns revert |
| return_volatility | risk | ts_std_dev, ts_delay | Recent volatility predicts stability |
| vwap_close_spread | microstructure | - | Close above VWAP = buying pressure |
| momentum_medium_term | momentum | ts_delta | 2-3 month momentum persists |
| rank_momentum_sector | momentum | group_rank, ts_delta | Sector-relative strength continues |
| ts_rank_returns | momentum | ts_rank | Stocks at historical highs trend |
| high_low_spread | volatility | - | Intraday range indicates uncertainty |
| open_close_ratio | microstructure | rank | Closing direction shows pressure |
| vwap_max_strength | momentum | rank, ts_max | Recent VWAP highs = strength |
| price_reversal_short | mean_reversion | ts_delta | Short-term reversals |
| winsorized_signal | cleaning_pattern | winsorize, ts_backfill | Standard data cleaning |
| group_zscore_sector | neutralization_pattern | group_mean, group_stddev | Standardize within groups |
| cap_decile_neutralized | neutralization_pattern | group_neutralize, bucket, rank | Remove cap bias |
| volume_gated_momentum | gating_pattern | trade_when, ts_delta | Trade only on volume |

**Added since this table was written** — rationale and citations live in the
templates' own docstrings. Eight came in with the `data/templates_pv_option.json`
batch: `capm_beta`, `momentum_66d`, `options_pcr_volume_gated`,
`price_reversal_5d`, `return_mean_20d`, `return_vol_20d`, `signed_power_transform`,
`vwap_max_13d`. Ten during the 2026-10-12/13 pushes (operator-census shapes,
forum-evidenced shapes, the dual-bucket recipe): `covariance_divergence`,
`double_gated_momentum`, `dual_bucket_neutralized`, `hump_turnover_controlled`,
`iv_skew_reversal`, `long_window_normalized`, `quality_gated_value`,
`tail_extreme_signal`, `ts_ir_trend`, `tvr_targeted_turnover`.

### 3. Forum-Mined Templates (1,277 fillable of 9,797 skeletons)
Community-contributed patterns from 99,666 forum posts and comments.

**File**: `docs/forum/forum_templates.json`
**Loader**: `generator/template_source.py`

**Statistics** (skeletons and fillable re-counted 2026-10-15; the rest from
the 2026-10-09 mine):
- Total distinct templates: 9,797
- Fillable from PV/options: 1,277
- Usable in the loaded pool: 512 of the 573 (see §5 for the rest)
- Seen in posts: 4,981; in comments: 4,379; in both: 407
- Default generation mix: 10% (configurable via `BRAIN_TEMPLATE_MIX`)

**Top forum patterns** (by post count):
1. `bucket(rank(cap), range='0,1,0.1')` - Cap decile bucketing (8 posts)
2. `ts_zscore()` - Time-series z-score (5 posts)
3. `ts_mean(close/ts_delay(close,1)-1, 20)` - 20d mean return (4 posts)
4. `ts_std_dev(close/ts_delay(close,1)-1, 20)` - 20d return volatility (4 posts)
5. `group_neutralize(signal, bucket(rank(cap), range='0.1,1,0.1'))` - Cap-neutral (4 posts)

### 4. Proven Templates (52 skeletons)

**File**: `docs/forum/proven_templates.json`
**Loader**: `generator/template_source.py` (same pool as the other corpora)

Skeletons taken from the expressions of alphas **the platform actually
accepted** — `dateSubmitted` set, `status=ACTIVE`. This is the one corpus whose
entries were not written down by anyone: every row is a shape that cleared
every submission check at least once.

Rebuilt on 2026-10-09 from the account's full acceptance list pulled from the
API (`GET /users/self/alphas`, then `GET /alphas/{id}` per alpha): **86 accepted
alphas, 69 distinct skeleton shapes**. Cross-referencing those 69 against every
corpus on disk (9,998 distinct shapes) left 58 that appear nowhere else; after
dropping multi-statement/ternary fragments and shapes fastplus rejects, **48
were added** to the 4 already there.

| | |
|---|---|
| Entries | 52 |
| Of which newly added 2026-10-09 | 48 |
| Fill test | all 52 fill to fastplus-valid expressions (60 draws each) |
| Accepted alphas represented | 86, across HKG/TOP800, EUR/TOP2500, USA/TOP3000, CHN/TOP2000U, IND/TOP500, KOR/TOP600, GLB/MINVOL1M |

**Most-accepted shape**: `rank(rank({f})/(1+days_from_last_change({f})))` — 4
separate accepted alphas share it, and it is in no other corpus.

**Why the size matters.** `_corpus_row_weights` gives each corpus a share going
as the square root of its usable size, so growing `proven` from 4 to 52 rows
raises its share roughly threefold (measured split before the change: forum
82%, cnhkmcp 8.1%, proven 6.6%, curated 3.3%). At 6.6% the corpus still
produced 2 of the 3 alphas accepted on 2026-10-09, both fillings of
`quantile(ts_rank({f},504))` — which is the evidence that this corpus is worth
more per row than the mined pools.

**Note on provenance.** Many source fields are outside the pv/option scope
(`fnd*`, `anl*`, `mdl*`, `probability_*`, `oth561_*`) — those alphas predate the
2026-10-02 data restriction. The skeletons carry `{f}` slots, not field names,
so they fill from the pv/option pool; `fillable_from_pv_option` is set on every
row and `generator/template_fill.py` re-checks the filled expression.

### 5. Help-Centre Templates (55 skeletons, 11 fillable, 1 new to the pool)

**File**: `docs/forum/help_center_templates.json`
**Harvest**: `docs/forum/help_center_articles.json` (602 articles, read-only)
**Loader**: `generator/template_source.py` (same pool as the other corpora)

The BRAIN help centre is a second Zendesk corpus, separate from the community
posts `tools/spider_forum.py` walks, and no miner in the tree read it until
2026-10-09. Its 602 articles page out in seven requests (the list endpoint
returns each body), and carry **59 expression-shaped lines**.

| | |
|---|---|
| Distinct skeletons | 55 |
| Fillable from pv/option | 11 |
| Rejected: foreign fields | 44 |
| Fillable but already in another corpus | 10 |
| **New usable rows** | **1** — `rank({f}) + rank({f})` |

The one that got in is worth the row it came from: the forum corpus holds the
same skeleton but flags it `fillable_from_pv_option: false`, because *some*
line that produced it used `book_to_price`/`earnings_yield`. The help centre's
line is `rank(close) + rank(volume)` — pv-native, so the shape enters the pool
with the flag set correctly. `forum-templates.md` measures the 1,926 other
shapes sitting behind that same all-or-nothing flag.

## Template Pipeline Standard

Community-standard template structure:
```
clean → combine → neutralize → transform
```

### Example Pipeline:
```python
# 1. Clean: backfill NaNs, winsorize outliers
cleaned = winsorize(ts_backfill(returns, 63), std=4.0)

# 2. Combine: time-series or cross-sectional operations
signal = ts_delta(cleaned, 66)

# 3. Neutralize: remove systematic biases
neutral = group_neutralize(signal, sector)

# 4. Transform: amplify extremes, decay, gate
final = signed_power(neutral, 0.5)
```

## Field Requirements

### PV (Price/Volume) Fields
**Dataset**: pv1, pv106, pv30, pv13, pv29

Common fields:
- Price: `close`, `open`, `high`, `low`, `vwap`
- Volume: `volume`, `adv20`
- Returns: `returns`
- Market cap: `cap`
- Microstructure: `bid_ask_price_gap`, `average_spread_slippage`

### Options Fields
**Dataset**: option3, option8, option9, option40

Common fields:
- Put/Call ratios: `pcr_oi_all`, `pcr_volume_all`
- Implied volatility: `iv_call_atm`, `iv_put_atm`
- Greeks: `delta_call`, `delta_put`, `gamma_call`, `gamma_put`, `vega_call`, `vega_put`, `theta_call`, `theta_put`

### Grouping Fields
- `sector`, `industry`, `subindustry`
- `country`
- PV30, PV13, PV29 classification fields

## Template Performance Tracking

Templates are tracked in the database via:
1. **Generation-time tracking**: `generator/weighted_selection` records which template created each expression
2. **Pattern matching**: `storage/track_signatures.py` regex patterns for historical expressions
3. **Performance table**: `template_performance` table stores (alpha_id, template_name, sharpe, fitness)

### Query Template Performance:
```sql
SELECT 
    template_name,
    COUNT(*) as count,
    AVG(is_sharpe) as avg_sharpe,
    AVG(fitness) as avg_fitness
FROM template_performance
GROUP BY template_name
ORDER BY avg_sharpe DESC;
```

## Template Selection Algorithm

Generation process uses weighted selection:

1. **Mix ratio**: 25% forum templates, 75% built-in (configurable)
2. **Diversity weighting**: Less-used operators get higher probability
3. **Pyramid targeting**: First slot filled from target pyramid category
4. **Validation**: All candidates validated before submission
5. **Cell context**: Performance history influences selection per (region, universe, delay, neutralization)

## Template Configuration

Environment variables:
- `BRAIN_TEMPLATE_MIX`: Fraction of forum templates (0.0-1.0, default 0.1)
- `BRAIN_RNG_SEED`: Seed for reproducible template selection
- `BRAIN_MAX_CONCURRENT`: Max concurrent simulations (default 8)

## References

- cnhkmcp templates: `docs/cnhkmcp-templates.md`
- Forum templates: `docs/forum-templates.md`
- PV/options documentation: `data/templates_pv_option.json`
- Template tracking: `storage/track_templates.py`
- Template signatures: `storage/track_signatures.py`

---
**Last Updated**: 2026-10-15
**Total Templates**: 48 built-in (10 cnhkmcp + 38 website) + 1,277 fillable
forum-mined (of 9,797 skeletons)
