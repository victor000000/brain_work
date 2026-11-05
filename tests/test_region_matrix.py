"""REGION_CONFIGS must only contain combos the platform actually offers.

The list was mirrored by hand and drifted: six combos (ILLIQUID_MINVOL1M in
USA/EUR/ASI, and MEA entirely) were rejected with HTTP 400 on every pick —
each one burned a full generation cycle plus a POST, 60 times in a single
day. `tools.discover_simulation_matrix` records the platform's own
OPTIONS /simulations answer; this diffs the list against it.

Skips when that artifact is absent (a clean checkout, or before the probe
has been run) — the same convention the other integration tests use.
"""

import json
import os

import pytest

from core.log_config import PROJECT_DIR
from core.regions import REGION_CONFIGS

# Resolved from PROJECT_DIR, not core.log_config.LOG_DIR: the test conftest
# redirects LOG_DIR into a sandbox, where this artifact never exists.
MATRIX_PATH = os.environ.get("BRAIN_LOG_DIR") or os.path.join(PROJECT_DIR, "brain_logs")
MATRIX_PATH = os.path.join(MATRIX_PATH, "discover_simulation_matrix.full.json")


@pytest.fixture
def platform_matrix():
    if not os.path.exists(MATRIX_PATH):
        pytest.skip("no discovered matrix — run `python -m tools.discover_simulation_matrix`")
    with open(MATRIX_PATH) as handle:
        data = json.load(handle)
    return {(region, universe, delay) for region, universe, delay in data["matrix"]}


def test_every_configured_combo_is_offered_by_the_platform(platform_matrix):
    rejected = [combo for combo in REGION_CONFIGS if combo not in platform_matrix]
    assert not rejected, f"configured but not offered (HTTP 400 on submit): {rejected}"


def test_no_duplicate_configs():
    assert len(REGION_CONFIGS) == len(set(REGION_CONFIGS))


def test_configs_are_well_formed():
    for region, universe, delay in REGION_CONFIGS:
        assert region and universe, (region, universe, delay)
        assert delay in (0, 1), (region, universe, delay)
