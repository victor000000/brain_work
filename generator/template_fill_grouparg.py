"""Where a group operator wants its group, and the check for the mirror slip.

Split out of `generator/template_fill_types.py`, which re-exports these names.
"""

from __future__ import annotations

import re

from generator.template_fill_args import _call_arguments
from generator.template_fill_tokens import GROUP_NAMES, SLOT

# Group-argument position per group operator, from the platform's definitions
# in the `operators` table (`group_rank(x, group)`, `group_mean(x, weight,
# group)`, `group_backfill(x, group, d, std=4.0)`). A heuristic, not a parser:
# operators missing from the table fall back to the last positional argument,
# where every documented `group_*` operator puts its group.
GROUP_ARG_INDEXES = {
    "group_rank": (1,),
    "group_zscore": (1,),
    "group_neutralize": (1,),
    "group_scale": (1,),
    "group_sum": (1,),
    "group_count": (1,),
    "group_std_dev": (1,),
    "group_backfill": (1,),
    "group_mean": (2,),
    "group_cartesian_product": (0, 1),
    # The only group-taking operator whose name does not start with `group_`.
    # It was therefore invisible to both checks that key on that prefix: a
    # MATRIX slot could fill it (rejected by the platform —
    # `densify(...), expected "Unit[Group:1]", found "Unit[]"`, 2026-10-09) and
    # a legitimate group field inside it was reported as a group read as a
    # series. Listing it here is what makes `wants_group` true for it.
    "densify": (0,),
}

# Operator names that take a group argument, whether or not they say so.
_GROUP_TAKING = frozenset(GROUP_ARG_INDEXES)


def wants_group(name: str) -> bool:
    """True when `name` has a position that must hold a GROUP.

    The prefix is the naming convention; `_GROUP_TAKING` is the list of
    operators that take one without following it. Both checks — the group
    argument's type and a group field read as a series — must agree on this,
    or an operator in the gap is judged by one and not the other.
    """
    low = name.lower()
    return low.startswith("group_") or low in _GROUP_TAKING


_NAMED_ARG_RE = re.compile(r"[a-z_][a-z0-9_]*\s*=.*", re.IGNORECASE)
_BARE_FIELD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def group_argument_indexes(name: str, args: list[str]) -> tuple[int, ...]:
    """Positions `name` wants a group at. See GROUP_ARG_INDEXES."""
    indexes = GROUP_ARG_INDEXES.get(name)
    if indexes is not None:
        return indexes
    positional = [a for a in args if not _NAMED_ARG_RE.fullmatch(a)]
    return (len(positional) - 1,)


def densify_slot_problem(skeleton: str) -> str | None:
    """A bare `{f}` standing in `densify`'s argument, or None.

    `densify`'s argument must be a group the *target cell* recognizes, and a
    slot cannot supply one: slots are filled from the union of every cell's
    fields (`prepare_pools(conn)` takes only `conn`), so `densify({f})` renders
    a field that is a GROUP somewhere and a plain series — or nothing at all —
    where the batch is actually going. The platform answers

        Incompatible unit for input of "densify" at index 0,
        expected "Unit[Group:1]"

    and the simulation is charged for no alpha. Measured 2026-10-11: **0 of
    214,359 stored alphas contain `densify(`**, against 5-15 emissions a day
    since 2026-10-09 — a 100% failure rate, not a slow path. All four shapes
    that emit it come from `docs/forum/proven_templates.json`, three as
    `densify({f})` and one as `densify(sector)`.

    A literal built-in group is the form that works: `densify(sector)` is valid
    in every cell, so a slotless argument is left alone and only the slot is
    rejected. A nested call (`densify(bucket(rank({f}), …))`) is also left
    alone — a `bucket` argument is a group the platform does build, and
    rejecting it would be an unmeasured over-rejection, which is the failure
    this project keeps paying for.

    The proper fix is cell-scoped group pools, which is a change to how
    generation caches (`prepare_pools`) rather than a check; this is the
    removal of a path with no measured success.
    """
    for name, args in _call_arguments(skeleton):
        if name.lower() == "densify" and any(a == SLOT for a in args):
            return "slot as densify argument"
    return None


def _bare_field(arg: str) -> str | None:
    """The name when `arg` is a lone identifier, else None.

    Only a bare name is judged — an argument that is itself a call may
    legitimately produce a series or a group, and the fields read inside it
    are the inner call's business. This is a token check, not type inference.
    """
    token = arg.strip()
    return token if _BARE_FIELD_RE.fullmatch(token) else None


def group_field_as_series(expr: str, group_fields=None) -> str | None:
    """A GROUP field read where a series is wanted, or None.

    The mirror of the group-argument check in `type_violation`: a field the
    platform types GROUP — a dataset grouping such as
    `technology_pca_factor2_grouping5`, or a built-in name like `market` —
    reaches an operator that wants a matrix and comes back

        Incompatible unit for input of "ts_arg_max" at index 0,
        expected "Unit[]", found "Unit[Group:1]"

    — a simulation spent for nothing (observed live 2026-10-06, and the
    largest single class in `sim_errors`). `group_name_as_series` catches the
    built-in names in a call that is not `group_*`, but a dataset field typed
    GROUP passes every check we have: it is a known field, so `field_violation`
    allows it, and only the `group_*` argument positions were ever compared
    against a type. A group field is valid *only* in a group slot, so anything
    else is reported here.

    `group_fields` is the typed pool when the caller has one; the built-in
    GROUP_NAMES are always treated as groups, since the platform defines them
    that way whatever the pool holds.
    """
    groups = set(group_fields or ()) | GROUP_NAMES
    for name, args in _call_arguments(expr):
        low = name.lower()
        wanted = group_argument_indexes(low, args) if wants_group(low) else ()
        positional = [a for a in args if not _NAMED_ARG_RE.fullmatch(a)]
        for index, arg in enumerate(positional):
            token = _bare_field(arg)
            if token in groups and index not in wanted:
                return f"{name}() takes a series at argument {index}, got the group field {token}"
    return None
