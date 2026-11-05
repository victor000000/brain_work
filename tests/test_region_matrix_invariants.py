"""Structural invariants of core.regions.REGION_CONFIGS.

These deliberately do NOT read their expectations back out of REGION_CONFIGS —
they pin the shape and ordering conventions that every consumer relies on, so
a malformed row fails here instead of mid-simulation.
"""

import re

from core.regions import REGION_CONFIGS

_REGION_RE = re.compile(r"^[A-Z]{2,4}$")
_UNIVERSE_RE = re.compile(r"^[A-Z0-9_]+$")


def test_matrix_is_not_empty():
    assert REGION_CONFIGS, "the simulation matrix is empty"


def test_every_entry_is_a_region_universe_delay_triple():
    for entry in REGION_CONFIGS:
        assert isinstance(entry, tuple), f"{entry!r} must be a tuple"
        assert len(entry) == 3, f"{entry!r} must be (region, universe, delay)"
        region, universe, delay = entry
        assert isinstance(region, str) and _REGION_RE.match(region), f"bad region: {entry!r}"
        assert isinstance(universe, str) and _UNIVERSE_RE.match(universe), f"bad universe: {entry!r}"
        assert isinstance(delay, int) and not isinstance(delay, bool), f"delay must be an int: {entry!r}"
        assert delay in (0, 1), f"delay must be 0 or 1: {entry!r}"


def test_matrix_has_no_duplicate_combos():
    assert len(REGION_CONFIGS) == len(set(REGION_CONFIGS))


def test_regions_form_contiguous_blocks():
    """Rows are grouped by region; a region appearing twice is a merge error."""
    seen = set()
    prev = None
    for region, _, _ in REGION_CONFIGS:
        if region != prev:
            assert region not in seen, f"{region} appears in more than one block"
            seen.add(region)
            prev = region


def test_delay_1_precedes_delay_0_within_each_universe():
    """Convention: a (region, universe) group lists delay 1 before delay 0."""
    seen = {}
    for region, universe, delay in REGION_CONFIGS:
        key = (region, universe)
        if delay == 1:
            assert seen.get(key) != 0, f"{key}: delay 0 listed before delay 1"
        seen[key] = delay


def test_core_regions_present():
    """A silent truncation of the matrix must fail loudly."""
    regions = {region for region, _, _ in REGION_CONFIGS}
    assert {"USA", "EUR", "GLB", "ASI", "CHN"} <= regions
