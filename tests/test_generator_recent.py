"""Cross-batch duplicate suppression in `collect_valid`.

Within one call a duplicate was already dropped; across calls nothing was, so a
slotless skeleton re-emitted the same string every time it was drawn. Measured
2026-10-07: 232 of ~1,700 fresh alphas were exact duplicates of an earlier one.
"""

import pytest

from generator import random_generator_rounds as rounds

POOLS = ({"close", "volume", "open"}, None, set(), set())


@pytest.fixture(autouse=True)
def _fresh_memory():
    rounds._recent.clear()
    rounds._recent_set.clear()
    yield
    rounds._recent.clear()
    rounds._recent_set.clear()


def _batch(expressions):
    """A `batch(n, allow_templates)` stub cycling through `expressions`."""
    state = {"i": 0}

    def batch(n, _allow_templates):
        out = []
        for _ in range(n):
            out.append(expressions[state["i"] % len(expressions)])
            state["i"] += 1
        return out

    return batch


def _generate(expressions, count):
    return rounds.collect_valid(_batch(expressions), POOLS, count, {"errors": 0}, "USA", "TOP3000", 1)


def test_a_duplicate_within_one_call_is_dropped():
    assert _generate(["rank(close)"], 3) == ["rank(close)"]


def test_an_expression_seen_in_an_earlier_call_is_skipped_for_a_fresh_one():
    """The generator gets another draw, which is what the memory is for."""
    first = _generate(["rank(close)", "rank(volume)"], 2)
    assert sorted(first) == ["rank(close)", "rank(volume)"]
    # The second call's first draw repeats `rank(close)`, which is in memory;
    # the next round offers something genuinely new and that is what comes back.
    second = _generate(["rank(close)", "rank(open)"], 1)
    assert second == ["rank(open)"], "the recent duplicate was re-emitted"


def test_a_small_pool_still_fills_rather_than_starving():
    """The last pass accepts a recent duplicate: a cell whose whole reachable
    space is already in memory must not shrink to an unsubmittable batch."""
    _generate(["rank(close)"], 1)
    assert _generate(["rank(close)"], 1) == ["rank(close)"]


def test_the_memory_is_bounded():
    for i in range(rounds._RECENT_LIMIT + 10):
        rounds._remember(f"rank(f{i})")
    assert len(rounds._recent) == rounds._RECENT_LIMIT
    assert len(rounds._recent_set) == rounds._RECENT_LIMIT
