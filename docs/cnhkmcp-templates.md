# Templates extracted from cnhkmcp 4.3.8

> Historical reference retained from the 2026 source snapshot. Counts, availability, thresholds and economic explanations below are dated observations or source claims, not current platform guarantees. For current admission and verification use [Research](RESEARCH.md); refresh native metadata/verdicts before spending quota. Raw corpora and account evidence are deployment-local and omitted from publication.
Source: `cnhkmcp/untracked/skills/brain-enhance-template/knowledge/template_final_enhance/`
(files `sample_prompt.md`, `op总结.md`, `单因子思考逻辑链.md`).

This is the template knowledge the package ships. Note that `cnhkmcp/knowledge/`
(40+ BRAIN documentation pages) is **byte-identical between 3.1.11 and 4.3.8** —
these skill files are where the template material actually lives.

## The house style

Every "enhanced template" in the source follows one pipeline:

```
clean  →  combine  →  neutralise  →  transform
ts_backfill(field, 63) → winsorize(..., std=4) → group_zscore(..., sector) → signed_power(..., 0.5)
```

The source states it directly: *"clean data (backfill, winsorize) → transform/
compare across time or peers → rank/neutralize → (optionally) decay/turnover
tune."*

`{}` marks a datafield **slot** — the point of a template is that fields are
substitutable while the operator skeleton and its rationale stay fixed.

## Named templates

### Price-native (work with pv fields as-is)

**1. CAPM residual** — strip market/sector beta to isolate idiosyncratic alpha
```
ts_regression(returns, group_mean(returns, log(ts_mean(cap, 21)), sector), 252, rettype=0)
```
Fields: `returns`, `cap` (both `pv1`) + a group field.
Rationale: sector-weighted by smoothed log-cap to reduce large-cap dominance.

**2. CAPM beta (slope)** — rank relative risk within sector
```
ts_regression(returns, group_mean(returns, log(ts_mean(cap, 21)), sector), 252, rettype=2)
```
Same fields. Pre-clean target/market with `ts_backfill(...,63)` + `winsorize(std=4)`.

**3. CAPM generalized to any feature** — remove the group-mean component
```
data     = winsorize(ts_backfill({data}, 63), std=4)
data_gpm = group_mean(data, log(ts_mean(cap, 21)), sector)
signal   = ts_regression(data, data_gpm, 252, rettype=0)
```
The substitution point for any pv field.

### Options-native

**6. Option Greeks net spread** — options-implied sentiment vs peers
```
group_operator(<put_greek> - <call_greek>, <grouping_data>)
```
Over industry/sector, for Delta/Gamma/Vega/Theta. Extend with multi-Greek
composites or time-series deltas. Maps onto the `option` category
(`option8` Volatility, `option40` Options Analytics, `option9`, `option3`).

### Not usable under the pv/option restriction

**4. Actual vs estimate spread** and **5. Analyst term-structure** both require
analyst fields (`anl14_mean_eps_*`, act/est). These cannot be filled from price
or options data and are recorded here only for completeness.

## Operator-selection guidance

`op总结.md` (20 KB) is a per-operator catalogue of *when to reach for it*,
grouped by class — arithmetic, logical, time-series, cross-sectional, group.
Representative rules:

| Operator | Use when |
|---|---|
| `signed_power(A, y)` | A has meaningful sign; amplify extremes without destroying it |
| `log` / `sqrt` | Distribution is right-skewed (volume, cap) — compress the tail, keep order |
| `s_log_1p` | Compress both tails of a zscore without breaking sign |
| `abs` | Direction irrelevant — distance from neutral is the signal |
| `if_else(cond, x, y)` | Only the tails carry signal; zero out the middle band |
| `trade_when(cond, new, old)` | Condition gates position changes |

`单因子思考逻辑链.md` (13 KB) is the reasoning chain for choosing operators
given a single factor A where higher = better.

## Filling these with pv/option fields

**Slot → field mapping available under the restriction:**

| Slot | pv/option candidates |
|---|---|
| `returns` | `returns` (pv1) |
| `cap` | `cap` (pv1) |
| price level | `close`, `open`, `high`, `low`, `vwap` (pv1) |
| volume | `volume`, `adv20` (pv1) |
| spread / microstructure | `bid_ask_price_gap`, `average_spread_slippage` (pv106) |
| `sector` / group | `sector`, `industry`, `subindustry`, plus pv30/pv13/pv29 classification fields |
| `<call_greek>` / `<put_greek>` | option8 / option40 / option9 / option3 fields |

**Open design question:** whether "fill" means a generator that substitutes
pv/option fields into these skeletons at runtime, or a one-shot expansion into
concrete expressions. See `docs/superpowers/plans/2026-10-02-master-roadmap.md`
Workstream 3.
