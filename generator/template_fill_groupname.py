"""A grouping name used where a data series is wanted.

Split out of `generator/template_fill_types.py`, which re-exports the name.
"""

from generator.template_fill_args import _call_arguments
from generator.template_fill_grouparg import wants_group
from generator.template_fill_tokens import GROUP_NAMES


def group_name_as_series(expr: str) -> str | None:
    """A built-in grouping name passed where a data series is expected, or None.

    The mirror of the group-argument check in `type_violation`. Mined skeletons
    carry literals like `ts_corr({f}, market, 20)`, which reads `market` as a
    data series and comes back from the platform

        Incompatible unit for input of "ts_corr" at index 1,
        expected "Unit[]", found "Unit[Group:1]"

    — a simulation spent for nothing. Both `field_violation` (via
    `unknown_field_tokens`) and the operator allowlist let these through:
    GROUP_NAMES are deliberately not dataset fields, so they are allowed as
    tokens and never checked against a type.

    A group name is valid only where an operator *wants* a group — those calls
    are skipped here and handled by the index table in `template_fill_grouparg`.
    That set was spelled `startswith(("vec_", "group_"))`, which skipped
    `vec_*` (handled separately) and every `group_*`, but not `densify`: a
    legitimate `densify(sector)` was reported as `sector` read as a series, and
    a `densify({f})` skeleton could never be filled at all.
    """
    for name, args in _call_arguments(expr):
        if name.lower().startswith("vec_") or wants_group(name):
            continue
        for arg in args:
            token = arg.strip()
            if token in GROUP_NAMES:
                return f"{name}() takes a matrix, got the group `{token}`"
    return None
