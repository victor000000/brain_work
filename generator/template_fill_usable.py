"""The load-time usability gate for a mined skeleton.

`is_usable` runs the token, allowlist and shape checks that reject a corpus row
before it can cost a fill and a parse on every draw. Split out of
`generator/template_fill.py`, which re-exports these names.
"""

from __future__ import annotations

import re

from generator.template_fill_grouparg import densify_slot_problem
from generator.template_fill_groupname import group_name_as_series
from generator.template_fill_tokens import SLOT, _value_tokens, field_violation, slot_count
from generator.validate import called_identifiers, parse_error

# Two slots with nothing but whitespace between them means the skeleton came
# from prose, not an expression: the miner accepts any line containing an
# operator call, so "Related trap that cost me… min(x, y)" survives, and
# stripping whitespace glues its words into one fake identifier. Filling that
# yields names like `sectorpv98_vwap_1430_backfill`, which fastplus accepts
# because any identifier is a valid call or variable.
_ADJACENT_SLOTS = re.compile(r"\{f\}\s*\{f\}")

# Stand-in for every slot when parsing a skeleton's shape. Deliberately a
# token that is neither a field nor an operator name: the parse must judge the
# skeleton's grammar and operator arity, not the field check — that runs
# separately, token by token, in `is_usable`.
_SLOT_STANDIN = "x"


def skeleton_shape_problem(skeleton: str, known_operators=None) -> str | None:
    """Parse problem with every slot stood in by a placeholder, or None.

    `is_usable` reads skeleton *tokens* — slots, operators, fields — but not
    shape: a prose fragment that merely contains an operator call ("sort by
    volume: rank({f}) on today's traded volume.") passes every token check and
    only fails after filling. In the live corpus that was ~70% of the loaded
    pool, each such row costing a fill and a fastplus parse on every draw.
    Parsing the skeleton once is microseconds and rejects the class at load.
    """
    return parse_error(skeleton.replace(SLOT, _SLOT_STANDIN), known_operators)


def is_usable(skeleton: str, known_fields, known_operators=None) -> bool:
    """True when the skeleton can produce an expression over real fields.

    Every value token — not just the tokens of slotless skeletons — must be a
    field from the pool or an allowed built-in name, and every function it
    calls must be a real operator (fastplus accepts invented ones). A slot does
    not launder the skeleton's literals: `rank({f}/assets)` fills fine and
    validates, but `assets` is not in the pool.

    A slotless skeleton gets no field substituted, so it must read at least one
    field itself. Otherwise it is a constant such as `ts_av_diff(185,5)`: it
    parses and simulates, but it evaluates no data and contributes nothing.
    """
    if _ADJACENT_SLOTS.search(skeleton):
        return False

    if known_operators is not None:
        invented = called_identifiers(skeleton) - set(known_operators)
        if invented:
            return False

    if skeleton_shape_problem(skeleton, known_operators) is not None:
        return False

    if field_violation(skeleton, known_fields) is not None:
        return False

    # A built-in grouping name in a series position. `field_violation` allows
    # these tokens on purpose — GROUP_NAMES are not dataset fields — so nothing
    # below catches them, and the `{f}` slots are not what is wrong: the
    # skeleton's own literal is. `ts_corr({f},market,20)` can never render a
    # valid expression whatever the pool, because no field substitution moves
    # `market` out of the series argument.
    #
    # Measured on the live pool 2026-10-11 over six cells: two forum skeletons
    # (`ts_rank(ts_corr({f},market,20),252)`, `ts_zscore(ts_corr({f},market,60),252)`)
    # rendered nothing valid in any of them — 12 dead (cell, skeleton) pairs, an
    # unreachable shape in every cell rather than a slow one. Same class as the
    # 21-of-38 built-ins that went unselectable, one level down.
    if group_name_as_series(skeleton) is not None:
        return False

    # A slot standing in for `densify`'s group argument. Same class as the
    # literal above, one level down: the skeleton's own shape cannot produce a
    # valid expression, because the group the slot would supply is drawn from
    # the global pool and the target cell's answer differs — see
    # `densify_slot_problem` for the measurement (0 successes in 214,359
    # stored alphas).
    if densify_slot_problem(skeleton) is not None:
        return False

    if slot_count(skeleton) == 0:
        return bool(_value_tokens(skeleton) & set(known_fields))
    return True
