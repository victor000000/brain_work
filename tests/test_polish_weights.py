"""Near-miss polishing: picking the next neutralization."""

import random

import pytest

from runner.explore_helpers import polish
from runner.settings_factory import ALLOWED_NEUT_BY_REGION
from tests.test_polish_helpers import _alpha, conn

__all__ = ["conn"]

# ---------------------------------------------------------- variant choice ---


def test_variant_neutralization_never_repeats_the_original():
    for _ in range(30):
        for region, allowed in ALLOWED_NEUT_BY_REGION.items():
            if not allowed:
                continue
            original = sorted(allowed)[0]
            got = polish.variant_neutralization(region, original)
            assert got != original
            assert got in allowed


def test_variant_neutralization_none_when_no_alternative():
    assert polish.variant_neutralization("HKG", "SLOW", random.Random(0)) is not None
    # A region with a single legal neutralization has nothing to vary to.
    import runner.explore_helpers.polish as module

    saved = module.ALLOWED_NEUT_BY_REGION
    try:
        module.ALLOWED_NEUT_BY_REGION = {"XXX": ["SLOW"]}
        assert module.variant_neutralization("XXX", "SLOW") is None
    finally:
        module.ALLOWED_NEUT_BY_REGION = saved


# ---------------------------------------------------------------- weights ---


def test_outcome_weights_smooth_and_rank(conn):
    """Passed neutralizations get a modest edge; untried ones stay at 0.5."""
    for i, (neut, fails) in enumerate([("RM", 0), ("RM", 0), ("RM", 1), ("FAST", 1), ("FAST", 1)]):
        _alpha(conn, aid=f"W{i}", neut=neut)
        conn.execute(
            "INSERT OR REPLACE INTO alpha_check_summary VALUES (?,?,?,?,?,?)",
            (f"W{i}", 14 - fails, fails, 5, 0, "2026-10-05"),
        )
    w = polish.outcome_weights(conn)
    assert w["RM"] == pytest.approx(3 / 5)  # (2 passes + 1) / (3 + 2)
    assert w["FAST"] == pytest.approx(1 / 4)  # (0 + 1) / (2 + 2)
    assert w.get("UNTRIED", 0.5) == 0.5  # unseen neutralizations default
    assert w["RM"] > w["FAST"]


def test_outcome_weights_empty_table_is_uniform(conn):
    assert polish.outcome_weights(conn) == {}


def test_variant_neutralization_respects_weights(conn):
    """A heavily-weighted neutralization should dominate a 200-draw sample."""
    import runner.explore_helpers.polish as module

    saved = module.ALLOWED_NEUT_BY_REGION
    try:
        module.ALLOWED_NEUT_BY_REGION = {"XXX": ["GOOD", "BAD"]}
        weights = {"GOOD": 0.9, "BAD": 0.05}
        rng = random.Random(7)
        picks = [module.variant_neutralization("XXX", "ORIG", rng, weights) for _ in range(200)]
        assert picks.count("GOOD") > 150, picks.count("GOOD")
    finally:
        module.ALLOWED_NEUT_BY_REGION = saved
