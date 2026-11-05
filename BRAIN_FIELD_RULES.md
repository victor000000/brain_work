# Data Field & Expression Rules

## Field Types & Operator Compatibility
Counts below are for the **current pv/option-only database** (post-prune,
2026-10-02). The pre-prune pool was ~5× larger across all categories.

| Field Type | Count | Use With |
|---|---|---|
| MATRIX | 142,990 | All time-series, cross-sectional, arithmetic ops |
| VECTOR | 9,883 | vec_sum, vec_avg ONLY (causes "event input" errors elsewhere) |
| GROUP | 8,780 | Group operator arguments, densify input, bucket input |
| UNIVERSE | 220 | Not used (metadata) |
| SYMBOL | 136 | Not used (identifiers) |

## Critical Rules (from errors)
- **vec_sum/vec_avg**: MUST use VECTOR fields, not MATRIX
- **densify**: MUST use GROUP fields (consolidates sparse groups)
- **bucket**: output IS a GROUP — MUST use inside group_rank/group_zscore/etc
- **rank()** strips units — safe wrapper for cross-unit operations
- **Group operators**: output is group-unit — wrap in rank() or use as group arg

## Group Arguments
- Built-in: sector, industry, subindustry, country, market, exchange, currency
- DB GROUP fields: 1,122 unique (cluster IDs, factor groups, etc.)
- bucket(rank(x), range="0,1,0.2") creates dynamic groups

## Operator Parameters
- ts_regression(y, x, d) — 3 args
- kth_element(x, d, k=N) — k must be positive integer
- bucket(x, range="0,1,0.2") — range required
- group_mean(x, weight, group) — 3 args
- group_backfill(x, group, d) — 3 args

## Field-Pool Filtering

The pool is filtered by **category**, not by an individual-field blocklist.

- `INCLUDE_CATEGORIES = ('pv', 'option')` in `generator/field_queries.py` is the
  single source of truth, applied by all three loaders
  (`query_matrix_fields`, `query_vector_fields`, `query_group_fields`) and by
  pyramid targeting in `diversity_picker/pyramid3.py`.
- Identifier fields are excluded from the MATRIX pool: `isin`, `cusip`, `date`,
  `timestamp`, `symbol`.

**Removed 2026-10-02:** the `field_blacklist` table and its loader filter.
`download/blacklist_group_unit.py` populated it by blacklisting *every* MATRIX
field appearing in a `Unit[Group:1]` failure, including incidental ones, and
only ever appended. Once price became the only pool that collateral dominated
small regions — CHN/TOP2000U/d0 fell to 1 usable field of 12, IND lost 85% of
its price pool. `find_group_unit_offenders()` remains in that module as a
diagnostic; it reads `simulations`, not the blacklist.

Some fields are typed MATRIX but carry group/cluster semantics (descriptions
like "Industry grouping using method 1 with 5 clusters"). Wrapping such a field
in a group-consuming operator still produces `Unit[Group:1]`. There is no
longer a table gating them, so this is a known source of wasted simulations.
