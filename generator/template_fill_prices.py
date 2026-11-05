"""Recover raw-price roles where a source example establishes unit coupling."""

import re
from functools import lru_cache

from generator.template_fill_bindings import infer_slot_bindings, infer_slot_sources
from generator.template_fill_tokens import SLOT
from generator.templates_brain_website_pick import (
    _OPEN_WINDOW_TOKENS,
    _PRICE_EXCLUDE,
    _PRICE_ROLES,
    _pick_price,
    _pick_price_set,
    _tokens,
)

_ARITHMETIC_PAIR = re.compile(r"(?=(\{f\}\s*[-+/]\s*\{f\}))")


def price_contract(skeleton, example):
    """Keep anonymous, nonmatching and unit-self-cancelling shapes unchanged."""
    return _contract(skeleton, example) if isinstance(example, str) else ()


def _price_role(field):
    tokens = _tokens(field)
    roles = tokens & set(_PRICE_ROLES)
    if tokens & set(_PRICE_EXCLUDE) or len(roles) != 1:
        return None
    role = next(iter(roles))
    return None if role == "open" and tokens & set(_OPEN_WINDOW_TOKENS) else role


@lru_cache(maxsize=4096)
def _contract(skeleton, example):
    sources = infer_slot_sources(skeleton, example)
    bindings = infer_slot_bindings(skeleton, example)
    if sources is None or bindings is None:
        return ()
    roles = {}
    for match in _ARITHMETIC_PAIR.finditer(skeleton):
        i = skeleton[: match.start()].count(SLOT)
        left, right = bindings[i : i + 2]
        if left == right:
            continue
        a, b = (_price_role(sources[j]) for j in (i, i + 1))
        if a and b:
            roles.update({left: a, right: b})
    return tuple(sorted(roles.items()))


def assign_price_slots(contract, fields, rng, preferred):
    """Reuse the built-in price picker, preferring one dataset for all roles."""
    roles = tuple(role for _binding, role in contract)
    pair = _pick_price_set(preferred, rng, *roles) if preferred else None
    if pair is None:
        pair = _pick_price_set(fields, rng, *roles)
    if pair is None:
        pair = tuple(_pick_price(fields, rng, role) for role in roles)
    if any(field is None for field in pair):
        return None
    return {binding: field for (binding, _role), field in zip(contract, pair, strict=True)}
