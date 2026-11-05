"""find_new_datasets — the subcategory scope filter."""

from tests.test_find_new_datasets_helpers import FakeBrain, Resp
from tools.find_new_datasets.api import fetch_subcategories


def test_fetch_subcategories_drops_out_of_scope_children():
    brain = FakeBrain(
        [
            Resp(
                200,
                [
                    {"id": "pv", "children": [{"id": "pv-price-volume"}, {"id": "pv-x"}]},
                    {"id": "model", "children": [{"id": "model-technical"}]},
                    {"id": "option", "children": [{"id": "option-option"}]},
                ],
            )
        ]
    )
    assert [c["id"] for c in fetch_subcategories(brain)] == ["pv-price-volume", "pv-x", "option-option"]
