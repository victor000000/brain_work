"""Field-type contract checks for a filled expression.

`fill_skeleton` draws every slot from the MATRIX pool, so a slot that lands
where the operator needs another type produces an expression the platform
rejects. Split out of `generator/template_fill.py`, which re-exports these
names.
"""

from __future__ import annotations

from generator.template_fill_args import _call_arguments, _positional_index
from generator.template_fill_grouparg import (  # noqa: F401
    GROUP_ARG_INDEXES,
    _bare_field,
    densify_slot_problem,
    group_argument_indexes,
    group_field_as_series,
    wants_group,
)
from generator.template_fill_groupname import group_name_as_series
from generator.template_fill_tokens import _value_tokens, field_violation
from generator.validate import parse_error


def type_violation(expr: str, matrix_fields, vector_fields=None, group_fields=None) -> str | None:
    """Field-type contract violations in a filled expression, or None.

    `fill_skeleton` draws every slot from the MATRIX pool, so a slot that lands
    where the operator needs another type produces an expression the platform
    rejects: a `vec_*` argument must be a VECTOR and a `group_*` group argument
    must be a GROUP field. Both are positive — a token is only reported when it
    is *known* to be of the wrong type; unknown names are left to
    `field_violation`/fastplus. The mirrors — a built-in grouping name, or a
    dataset field typed GROUP, read as a series — are
    `template_fill_groupname.group_name_as_series` and
    `template_fill_grouparg.group_field_as_series`.
    """
    groups = set(group_fields or ())
    vectors = set(vector_fields or ())
    non_vector = (set(matrix_fields) | groups) - vectors
    # A field recorded as BOTH a group and a series is ambiguous, and the
    # platform reads it as a series where a group is required. 1,277 fields are
    # GROUP+MATRIX, and the duplication is structural: the same id is a
    # different type in a different universe (`top2000_factor8_value` is GROUP
    # in TOP3000/TOP1000/TOP500/TOP200 and MATRIX in ILLIQUID_MINVOL1M/TOP2000),
    # while the pools are built globally — `prepare_pools(conn)` takes only
    # `conn` — so the union of those answers is "both", and "both" used to read
    # as a valid group.
    #
    # Reading ambiguity as "not a group" is the direction that over-rejects, and
    # it is the cheap one: a rejected expression is redrawn, while a wrong one
    # costs a simulation. Measured over stored alphas, ambiguous fields carry 23
    # of 34,717 bare-field group arguments (0.07%), against a `densify` path
    # whose failure rate is 100% — it appears in 0 of 214,359 stored alphas.
    plain_mismatch = (set(matrix_fields) | vectors) - groups
    ambiguous = set(matrix_fields) & groups
    non_group = plain_mismatch | ambiguous

    problem = group_name_as_series(expr)
    if problem is not None:
        return problem
    problem = group_field_as_series(expr, groups)
    if problem is not None:
        return problem

    for name, args in _call_arguments(expr):
        low = name.lower()
        if low.startswith("vec_"):
            for arg in args:
                bad = _value_tokens(arg) & non_vector
                if bad:
                    return f"{name}() takes a VECTOR, got {', '.join(sorted(bad))}"
        elif wants_group(low):
            for index in group_argument_indexes(low, args):
                arg = _positional_index(args, index) if index >= 0 else None
                if not arg:
                    continue
                # Only a *bare* field is judged. An argument that is itself a
                # call may legitimately produce a group — `group_neutralize(x,
                # bucket(rank(cap), range='0,1,0.1'))` is the documented way to
                # neutralize by cap decile, and reading the field inside
                # `bucket(...)` as the group argument rejected it. This is a
                # token check, not a type inference, so anything compound is
                # left to the platform.
                token = _bare_field(arg)
                if token is not None and token in non_group:
                    return f"{name}() takes a GROUP, got {token}"
    return None


def filled_expression_problem(
    expr: str, known_fields, known_operators=None, vector_fields=None, group_fields=None
) -> str | None:
    """First problem with a filled expression: syntax, allowlist, field, type."""
    problem = parse_error(expr, known_operators)
    if problem is not None:
        return problem
    # The *membership* check takes every pool a slot can legitimately be filled
    # from; the *type* check takes the MATRIX pool alone, because "used as a
    # series" is defined against it. Passing only `known_fields` here reported a
    # group or vector field filled into its own slot as "unknown field(s)",
    # which is why role-aware filling (`template_fill_role`) needs this line.
    known = set(known_fields) | set(vector_fields or ()) | set(group_fields or ())
    problem = field_violation(expr, known)
    if problem is not None:
        return problem
    return type_violation(expr, known_fields, vector_fields, group_fields)
