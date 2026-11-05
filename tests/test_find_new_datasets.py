"""find_new_datasets — scope filtering and pagination.

The scan used to flatten every category (reporting out-of-scope datasets as
new) and never sent `offset`, so it missed everything past page 1.
"""

from tests import test_find_new_datasets_helpers as helpers
from tests.test_find_new_datasets_helpers import FakeBrain, Resp, field
from tools.find_new_datasets.scan import scan_subcat_for_new

# Bound here rather than imported by name: a direct import of `one_combo`
# would be shadowed by the test parameters of the same name (ruff F811).
one_combo = helpers.one_combo


def test_scan_walks_every_page(one_combo):
    brain = FakeBrain(
        [
            Resp(200, {"results": [field("a")], "count": 3}),
            Resp(200, {"results": [field("b"), field("c")], "count": 3}),
        ]
    )
    found = {}
    calls = scan_subcat_for_new(brain, "pv-price-volume", set(), found)
    assert calls == 2
    assert set(found) == {"a", "b", "c"}
    assert brain.calls[1]["offset"] == 1


def test_scan_stops_when_the_count_is_reached(one_combo):
    brain = FakeBrain([Resp(200, {"results": [field("a"), field("b")], "count": 2})])
    found = {}
    assert scan_subcat_for_new(brain, "pv-price-volume", set(), found) == 1
    assert set(found) == {"a", "b"}


def test_scan_ignores_out_of_scope_results(one_combo):
    brain = FakeBrain(
        [
            Resp(200, {"results": [field("mdl1", cat="model"), field("pv1")], "count": 2}),
        ]
    )
    found = {}
    scan_subcat_for_new(brain, "pv-price-volume", set(), found)
    assert set(found) == {"pv1"}


def test_scan_skips_known_datasets(one_combo):
    brain = FakeBrain([Resp(200, {"results": [field("a"), field("b")], "count": 2})])
    found = {}
    scan_subcat_for_new(brain, "pv-price-volume", {"a"}, found)
    assert set(found) == {"b"}
