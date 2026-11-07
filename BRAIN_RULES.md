# BRAIN Platform Rules — Quick Reference

> Historical reference retained from the 2026 source snapshot. Counts, availability, thresholds and economic explanations below are dated observations or source claims, not current platform guarantees. For current admission and verification use [Research](docs/RESEARCH.md); refresh native metadata/verdicts before spending quota. Raw corpora and account evidence are deployment-local and omitted from publication.
## Rate Limits
- Daily simulations: 5,000 (resets EST midnight)
- Concurrent: 8 parent sims max
- Auth API: 5 req/min
- Poll: Retry-After header (5s typical)
- Multi-sim: 2-10 expressions per POST (1 = single object)

## Regions & Universes
See `core/regions.py` — `REGION_CONFIGS` holds 39 (region, universe, delay)
combos across 11 regions and 17 universes. `download/fetch_fields.py` derives
its matrix from that list rather than restating it.

The platform's OPTIONS /simulations matrix offers 44; the five this list omits
are omitted for two different reasons, both recorded at the bottom of
`core/regions.py`:

- **ALL/LARGE, ALL/MEDIUM, ALL/SMALL** — in the matrix, and `/data-fields`
  answers for them, but `POST /simulations` returns
  `Region ALL is not available for simulation type REGULAR`. Confirmed by
  `tools/probe_simulation_combos` on 2026-10-09.
- **DEU/TOP500/d0, GBR/TOP700/d0** — the fields exist (126 and 122 MATRIX rows)
  but every one reports `coverage: 0.0`, so `field_queries_matrix` yields an
  empty pool and generation produces nothing.

This number has been wrong in the docs twice, so it is worth stating how it
moves: it read 41 / 9 / 18 until 2026-10-09, the count *before* the 2026-10-03
verification pruned the six combos the platform rejects with HTTP 400
(MEA/TOP300 and the three ILLIQUID_MINVOL1M cells). The code was updated that
day and the docs were not, leaving 35 / 8 / 16. Nine more were then added —
and five of those nine turned out to be unusable, which is the case
`tools/probe_simulation_combos` exists to catch and did.

## Data Restriction
Generation uses **price (`pv`) and options (`option`) data only**. Enforced by
`INCLUDE_CATEGORIES` in `generator/field_queries.py`, shared by the field
loaders and by pyramid targeting. All other categories were deleted from the
database on 2026-10-02.

Options data exists only in USA and IND; other regions are price-only.

## Neutralizations (11)
MARKET, SECTOR, INDUSTRY, SUBINDUSTRY, NONE,
SLOW_AND_FAST, SLOW, FAST, CROWDING,
REVERSION_AND_MOMENTUM, STATISTICAL

## Operators
83 total, 66 accessible (level=ALL), 17 restricted.
See `operators` table in DB for signatures.

## Field Types
MATRIX, VECTOR, GROUP, SYMBOL, UNIVERSE.
See `BRAIN_FIELD_RULES.md` for usage rules.
