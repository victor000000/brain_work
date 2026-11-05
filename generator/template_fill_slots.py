"""Slot filling and validated generation from mined skeletons.

Split out of `generator/template_fill.py`, which re-exports these names.
"""

from __future__ import annotations

import random

from generator.template_fill_bindings import infer_slot_bindings
from generator.template_fill_prices import assign_price_slots, price_contract
from generator.template_fill_role import slot_roles
from generator.template_fill_tokens import SLOT, _value_tokens
from generator.template_fill_types import filled_expression_problem
from generator.template_fill_usable import is_usable

# How many distinct templates `next_expression`/`generate_from_templates` try
# before giving up on a pool.
FILL_ATTEMPTS = 20


def fill_skeleton(
    skeleton: str,
    fields,
    rng: random.Random,
    first_pool=None,
    group_fields=None,
    vector_fields=None,
    slot_bindings: tuple[int, ...] | None = None,
    example=None,
) -> str:
    """Replace every `{f}` with a field drawn from `fields`.

    Slots draw independently unless source-example bindings tie repeated
    references to one chosen field. Typed positions also constrain the pool:
    a `group_*` group argument, `densify`, or a `vec_*` vector argument
    draws from `group_fields` /
    `vector_fields` instead (see `generator/template_fill_role.py` for why).
    When the matching pool is empty the slot falls back to `fields`, which is
    the old behaviour: the candidate is then invalid, and the caller's
    validation rejects it exactly as before.

    `first_pool`, when non-empty, supplies the first *series* slot's field. That
    is how pyramid targeting reaches templates: built-ins guarantee a field from
    the target pyramid via `pick_matrix`, and without this templates ignored the
    target the explorer had already chosen. An empty pool is treated as
    "no preference" so an unsatisfiable target degrades instead of failing.
    """
    if not fields:
        raise ValueError("cannot fill a skeleton with an empty field pool")
    if slot_bindings is not None and len(slot_bindings) != skeleton.count(SLOT):
        raise ValueError("source bindings must match every slot")
    assigned: dict[int, str] = {}
    preferred = list(first_pool) if first_pool else []
    contract = price_contract(skeleton, example)
    inferred = infer_slot_bindings(skeleton, example) if contract else None
    if contract and (slot_bindings is None or slot_bindings == inferred):
        slot_bindings = inferred
        prices = assign_price_slots(contract, fields, rng, preferred)
        if prices is None:
            return ""
        assigned.update(prices)
    price_bindings = set(assigned)
    groups = list(group_fields or ())
    vectors = list(vector_fields or ())
    roles = {start: pool for start, _end, pool in slot_roles(skeleton)}

    def draw(index: int) -> str:
        pool = roles.get(index)
        if pool == "group" and groups:
            return rng.choice(groups)
        if pool == "vector" and vectors:
            return rng.choice(vectors)
        return rng.choice(fields)

    out, start, filled_any = [], 0, False
    slot_index = 0
    while True:
        i = skeleton.find(SLOT, start)
        if i == -1:
            out.append(skeleton[start:])
            break
        out.append(skeleton[start:i])
        binding = slot_bindings[slot_index] if slot_bindings is not None else slot_index
        if binding in assigned:
            out.append(assigned[binding])
        else:
            field = rng.choice(preferred) if preferred and not filled_any and roles.get(i) is None else draw(i)
            assigned[binding] = field
            out.append(field)
        if binding not in price_bindings or _value_tokens(assigned[binding]) & set(preferred):
            filled_any = True
        slot_index += 1
        start = i + len(SLOT)
    return "".join(out)


def generate_from_templates(
    templates,
    fields,
    count: int,
    rng: random.Random,
    known_operators=None,
    vector_fields=None,
    group_fields=None,
) -> list[str]:
    """Produce up to `count` validated expressions by filling skeletons.

    Pass `known_operators` (see `validate.load_operator_names`) or the result
    is only syntax-checked, and the mined corpus contains invented operators
    that fastplus waves through. `vector_fields`/`group_fields` (the typed
    pools, when known) enable the `vec_*`/group-argument type checks.

    Templates whose filled output fails validation are dropped, so this may
    return fewer than `count` — or nothing — when the pool is poor.
    """
    if not templates or not fields or count <= 0:
        return []

    usable = [t for t in templates if is_usable(t["skeleton"], fields, known_operators)]
    if not usable:
        return []

    out: list[str] = []
    seen: set[str] = set()
    for _ in range(count * 20):
        if len(out) >= count:
            break
        template = rng.choice(usable)
        expr = fill_skeleton(
            template["skeleton"],
            fields,
            rng,
            group_fields=group_fields,
            vector_fields=vector_fields,
            slot_bindings=infer_slot_bindings(template["skeleton"], template.get("example")),
            example=template.get("example"),
        )
        if not expr or expr in seen:
            continue
        seen.add(expr)
        problem = filled_expression_problem(expr, fields, known_operators, vector_fields, group_fields)
        if problem is None:
            out.append(expr)
    return out
