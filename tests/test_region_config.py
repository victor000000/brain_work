"""The (region, universe, delay) matrix must have exactly one definition.

`download/fetch_fields.REGION_CONFIG` used to restate the matrix by hand
alongside `core.regions.REGION_CONFIGS`, and the copies drifted: CHN's delays
were [1, 0] in one and [0, 1] in the other. The downloader's copy is derived
from the canonical list, so these tests pin the relationship.
"""

from core.regions import REGION_CONFIGS
from download.fetch_fields import REGION_CONFIG


def _derived():
    return [
        (region, universe, delay)
        for region, cfg in REGION_CONFIG.items()
        for universe in cfg["universes"]
        for delay in cfg["delays"]
    ]


def test_region_config_derives_from_the_canonical_matrix():
    """Same combos — no region/universe/delay invented or dropped."""
    assert set(_derived()) == set(REGION_CONFIGS)


def test_region_config_order_matches_the_canonical_matrix():
    """Order matters for download sequencing; drift here is silent."""
    assert _derived() == list(REGION_CONFIGS)


def test_every_region_has_at_least_one_universe_and_delay():
    for region, cfg in REGION_CONFIG.items():
        assert cfg["universes"], f"{region} has no universes"
        assert cfg["delays"], f"{region} has no delays"


def test_downloader_config_shape():
    """Every derived region entry has exactly the keys the downloader consumes."""
    for region, cfg in REGION_CONFIG.items():
        assert set(cfg) == {"universes", "delays"}, f"unexpected keys for {region}: {sorted(cfg)}"
        assert all(isinstance(u, str) and u for u in cfg["universes"])
        assert all(isinstance(d, int) and d in (0, 1) for d in cfg["delays"])
