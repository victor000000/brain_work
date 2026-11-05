"""Shared eligibility gate for the local pre-submission filter.

These thresholds mirror the platform's must-pass checks documented in
BRAIN_SUBMIT_RULES.md / BRAIN_CONSTRAINTS.md so we stop wasting submit
attempts on alphas that will obviously fail.

Single source of truth — tune thresholds here and every submit tool picks
up the new values on next run.

Out of scope (cannot be enforced from alpha_results alone):
  - IS_LADDER_SHARPE: async-only platform check.
  - Coverage: column lives in `fields`, not `alpha_results`.
"""

from __future__ import annotations

# Default sharpe floor — EUR/d1 (~1.58) is the conservative cross-region default.
MIN_SHARPE_DEFAULT = 1.58

# Per-(region, delay) sharpe floors, taken from the LOW_SHARPE limits the
# platform itself returned in check bodies (recorded in `submission_checks`).
# Measured 2026-10-03 across regions: HKG/IND/KOR/USA/EUR/GLB/ASI/MEA = 1.58,
# CHN = 2.07. The earlier guesses (HKG/IND/KOR 1.85, USA 1.65) were not
# evidence-based and silently skipped submittable alphas. Some alphas are
# checked against a higher tier (USA/EUR 2.69, CHN 3.49) — those attempts are
# rejected by the platform, which is cheaper than never attempting.
# Missing entries fall back to MIN_SHARPE_DEFAULT.
REGION_DELAY_MIN_SHARPE = {
    ("CHN", 0): 2.07,
    ("CHN", 1): 2.07,
    ("HKG", 1): 1.58,
    ("IND", 1): 1.58,
    ("KOR", 1): 1.58,
    ("USA", 0): 1.58,
    ("USA", 1): 1.58,
    ("EUR", 0): 1.58,
    ("EUR", 1): 1.58,
    ("GLB", 1): 1.58,
    ("ASI", 1): 1.58,
    ("MEA", 1): 1.58,
}

# Fitness floor — BRAIN_SUBMIT_RULES.md LOW_FITNESS rule.
MIN_FITNESS = 1.0

# Turnover band — BRAIN_SUBMIT_RULES.md TURNOVER rule.
TURNOVER_MIN = 0.01
TURNOVER_MAX = 0.7

# Per-region turnover *ceiling*, from the HIGH_TURNOVER limits the platform
# itself returned in check bodies (`submission_checks`). Every region measured
# returns 0.7 except IND, which returns **0.4** across 356 check rows. The
# sharpe floors below have been per-cell since 2026-10-03; this band was still
# one global number, so an IND alpha with turnover in (0.4, 0.7] passed the
# local gate and was sent to a check that could only fail it — 13 such alphas
# on record, out of 391 IND alphas sitting in that band at all.
#
# Missing entries fall back to TURNOVER_MAX, so a region nobody has measured
# behaves exactly as it did before.
REGION_MAX_TURNOVER = {
    "IND": 0.4,
}

# Out-of-sample sanity floor — preserves the original "test_sharpe > 0" gate.
MIN_TEST_SHARPE = 0

# Backwards-compatibility alias for callers that still import MIN_SHARPE.
MIN_SHARPE = MIN_SHARPE_DEFAULT


def build_eligibility_union() -> str:
    """Return a SQL WHERE fragment that applies per-(region, delay) sharpe
    thresholds to known cells and the global default elsewhere.

    Returns the global no-arg clause when REGION_DELAY_MIN_SHARPE is empty
    (degenerate case; SQLite would otherwise reject the empty NOT ()).
    """
    cells = sorted(REGION_DELAY_MIN_SHARPE)
    if not cells:
        return eligibility_clause()
    parts = [
        f"(region='{region}' AND delay={delay} AND {eligibility_clause(region, delay)})" for (region, delay) in cells
    ]
    known = " OR ".join(f"(region='{r}' AND delay={d})" for (r, d) in cells)
    # The fallback covers cells in neither map, and those keep the global
    # turnover ceiling. That is correct rather than merely convenient: the one
    # region with a non-default ceiling, IND, is configured at delay 1 alone
    # (`core/regions.py`), and ("IND", 1) is in `REGION_DELAY_MIN_SHARPE`, so
    # it always resolves through the per-cell clauses above and never reaches
    # this branch. A region added at a second delay would need its entry in
    # `REGION_DELAY_MIN_SHARPE` too — which is the coupling to fix then, not a
    # silent 0.7 here.
    parts.append(f"(NOT ({known}) AND {eligibility_clause()})")
    return "(" + " OR ".join(parts) + ")"


def eligibility_clause(region: str | None = None, delay: int | None = None) -> str:
    """Return the shared SQL WHERE fragment, parenthesized for safe stitching.

    With no args, returns the global default (EUR/d1 conservative floor).
    With (region, delay), returns a clause using the region-specific floor.

    Callers compose it with their own filters using AND, e.g.:

        f"SELECT ... FROM alpha_results WHERE {eligibility_clause()} AND ..."

    or per-cell:

        f"SELECT ... FROM alpha_results WHERE {eligibility_clause(region, delay)} ..."
    """
    known = region is not None and delay is not None
    threshold = REGION_DELAY_MIN_SHARPE.get((region, delay), MIN_SHARPE_DEFAULT) if known else MIN_SHARPE_DEFAULT
    ceiling = REGION_MAX_TURNOVER.get(region, TURNOVER_MAX) if known else TURNOVER_MAX
    return (
        f"(is_sharpe >= {threshold}"
        f" AND is_fitness >= {MIN_FITNESS}"
        f" AND is_turnover BETWEEN {TURNOVER_MIN} AND {ceiling}"
        f" AND test_sharpe > {MIN_TEST_SHARPE})"
    )
