"""Re-run a near-miss in a *different* cell — the untried polish axis.

Same-cell polish varies only the neutralization, and the cell that supplies the
queue is the one saturating on `SELF_CORRELATION`: on 2026-10-07 the first check
run after the cap lifted failed four HKG/TOP800/d1 alphas at 0.77 against a 0.70
limit. Re-simulating the same expression somewhere else produces a different
return stream, which is what a correlation-bound gate needs and what
neutralization alone cannot supply.

Feasible, and measured rather than assumed: of the 191 queued candidates, 190
read only fields that exist in at least one other configured cell, and 152 exist
in six other regions (ASI, EUR, GLB, IND, KOR, USA).

Two hard gates, because a cross-cell submission is a simulation spent:

* **Every field must exist in the target cell.** Checked in SQL before the
  expression is considered, so a name that is HKG-only can never be posted to
  USA.
* **The expression is re-validated against the target's own pools.** The
  generator's own `filled_expression_problem` runs against the target's MATRIX /
  VECTOR / GROUP sets, so a field that is a GROUP there and a MATRIX here is
  caught before it costs a batch — the failure mode that produced the largest
  class in `sim_errors`.
"""

import random

from core.regions import REGION_CONFIGS
from generator.field_validation_pools import validation_pools
from generator.template_fill import filled_expression_problem
from generator.template_fill_tokens import _value_tokens
from generator.validate import load_operator_names

# One polish batch in this many moves to a different cell. Deterministic on
# `batch_idx` for the same reason POLISH_EVERY is: a ~4% chance per batch is
# unverifiable from the outside, and the results have to be attributable
# afterwards (`simulate.log` maps every batch to the alphas it produced). It is
# also a bounded share of the budget — polish is every other batch at three
# expressions, so this is ~4% of all expressions, against a hypothesis that has
# not been measured yet.
CROSS_CELL_EVERY = 4

# Cells that hold every one of these field names, as (region, universe, delay).
_CELLS_WITH_ALL = """
SELECT region, universe, delay FROM data_fields
WHERE id IN ({placeholders})
GROUP BY region, universe, delay
HAVING COUNT(DISTINCT id) = ?
"""


def cells_holding(conn, fields):
    """Every **configured** (region, universe, delay) holding all of `fields`.

    `data_fields` carries cells the platform will not simulate, and the query
    used to return them. Measured live 2026-10-11: batch B128 went to
    `ALL/LARGE/d1` and came back

        HTTP 400 {"settings": {"region": ["Region ALL is not available for
        simulation type REGULAR."]}}

    — a batch spent on a cell that cannot run anything. `REGION_CONFIGS` is the
    matrix every other part of the pipeline draws from, including the field
    download itself, so restricting to it is what the module docstring already
    claimed ("fields that exist in at least one other *configured* cell").
    """
    names = sorted(fields)
    if not names:
        return []
    configured = {(r, u, d) for r, u, d in REGION_CONFIGS}
    placeholders = ",".join("?" * len(names))
    rows = conn.execute(_CELLS_WITH_ALL.format(placeholders=placeholders), [*names, len(names)]).fetchall()
    return [(r, u, d) for r, u, d in rows if (r, u, d) in configured]


def target_pools(conn, region, universe, delay):
    """Complete eligible (matrix, vector, group) sets, without generation caps."""
    return validation_pools(conn, region, universe, delay)


def cross_cell_target(conn, expressions, home_cell, rng=None, operators=None):
    """A cell other than `home_cell` that can run all of `expressions`, or None.

    Prefers another *region* — a sibling universe changes the instrument set but
    not the market, and it is the market exposure that production correlation
    compares. A same-region cell is the fallback, not the target.
    """
    rng = rng or random.Random()
    fields = set()
    for expr in expressions:
        fields |= _value_tokens(expr)
    if not fields:
        return None

    candidates = [c for c in cells_holding(conn, fields) if c != tuple(home_cell)]
    if not candidates:
        return None
    other_region = [c for c in candidates if c[0] != home_cell[0]]
    candidates = other_region or candidates
    rng.shuffle(candidates)

    operators = operators if operators is not None else load_operator_names(conn)
    for region, universe, delay in candidates:
        matrix, vectors, groups = target_pools(conn, region, universe, delay)
        if all(filled_expression_problem(expr, matrix, operators, vectors, groups) is None for expr in expressions):
            return region, universe, delay
    return None
