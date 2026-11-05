"""Choose price fields with the same explicit name context."""

import re

from generator.templates_brain_website_pick import _PRICE_EXCLUDE, _PRICE_ROLES, _maybe_backfill, _tokens


def _pick_matching_prices(fields, rng, requested_roles):
    """Return a matched range triple, or None when no complete family exists.

    Native pv37 metadata calls high_10 a ten-day high and low_1430 a
    14:30 low. Sharing a dataset does not make those one measured range.
    Replace only the single price-role token and require every other token
    to match. Preserve suffixes literally: no inferred timestamp aliases or
    horizon conversions. This structural check is not metadata-level proof
    of adjustment consistency.
    """
    families = {}
    for field in fields:
        tokens = _tokens(field)
        roles = tokens & set(_PRICE_ROLES)
        if len(roles) != 1 or tokens & set(_PRICE_EXCLUDE):
            continue
        role = next(iter(roles))
        if role not in requested_roles:
            continue
        parts = tuple(part for part in re.split(r"[^a-z0-9]+", field.lower()) if part)
        family = tuple("<price>" if part == role else part for part in parts)
        families.setdefault(family, {}).setdefault(role, []).append(field)
    complete = [family for family in families.values() if all(family.get(role) for role in requested_roles)]
    if not complete:
        return None
    chosen = rng.choice(complete)
    return tuple(_maybe_backfill(rng.choice(chosen[role])) for role in requested_roles)


def pick_range_prices(fields, rng):
    """Match high, low and close without mixing explicit window contexts."""
    return _pick_matching_prices(fields, rng, ("high", "low", "close"))


def pick_vwap_prices(fields, rng):
    """Match close and VWAP, preserving session and backfill suffixes.

    Native pv98_close_16 is a 16:00 close, while pv98_vwap_1430 is a
    14:30 VWAP. Sharing a dataset does not make them one contemporaneous
    close/VWAP pair. Explicit cross-window hypotheses belong in separate
    templates; a missing matched pair does not justify an unrelated draw.
    """
    return _pick_matching_prices(fields, rng, ("close", "vwap"))
