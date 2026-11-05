"""find_new_datasets — error stops, the page cap and seen-combo bookkeeping."""

from tests import test_find_new_datasets_helpers as helpers
from tests.test_find_new_datasets_helpers import FakeBrain, Resp, field
from tools.find_new_datasets.scan import scan_subcat_for_new

# Bound here rather than imported by name: a direct import of `one_combo`
# would be shadowed by the test parameters of the same name (ruff F811).
one_combo = helpers.one_combo


def test_scan_stops_on_http_error(one_combo):
    brain = FakeBrain([Resp(200, {"results": [field("a")], "count": 50}), Resp(429, {})])
    found = {}
    assert scan_subcat_for_new(brain, "pv-price-volume", set(), found) == 2
    assert set(found) == {"a"}


def test_scan_is_capped_at_max_pages(one_combo):
    from tools.find_new_datasets._config import MAX_PAGES

    # `count` never satisfied: every page returns one row.
    brain = FakeBrain([Resp(200, {"results": [field("a")], "count": 10**9}) for _ in range(MAX_PAGES)])
    found = {}
    calls = scan_subcat_for_new(brain, "pv-price-volume", set(), found)
    assert calls == MAX_PAGES
    assert len(brain.calls) == MAX_PAGES
    assert brain.calls[-1]["offset"] == MAX_PAGES - 1  # each page advanced by one
    assert set(found) == {"a"}


def test_scan_builds_seen_combos(one_combo):
    brain = FakeBrain(
        [
            Resp(200, {"results": [field("a")], "count": 1}),
        ]
    )
    found = {}
    scan_subcat_for_new(brain, "pv-price-volume", set(), found)
    assert found["a"]["seen"] == [("USA", "TOP3000", 1)]
    assert found["a"]["subcategory"] == "pv-price-volume"
