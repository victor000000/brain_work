"""A malformed count or page is an error, not an empty result.

`_get_field_count` returning 0 for a malformed 200 body made the walk think a
region had no fields, permanently; the page-level walk must report the failure
rather than a short list.
"""

from download.fetch_paginate import _get_field_count, _paginate_fields
from tests.test_fetch_completeness_helpers import FakeBrain, Resp, _field

# ── _get_field_count ──────────────────────────────────────────────


def test_field_count_returns_the_count():
    brain = FakeBrain([Resp(200, {"count": 7, "results": []})])
    assert _get_field_count(brain, "USA", "TOP3000", 1, "pv-price-volume") == 7


def test_field_count_non_dict_200_is_an_error_not_zero():
    brain = FakeBrain([Resp(200, ["not", "a", "dict"])])
    assert _get_field_count(brain, "USA", "TOP3000", 1, "pv-price-volume") is None


def test_field_count_missing_count_key_is_an_error():
    brain = FakeBrain([Resp(200, {"results": []})])
    assert _get_field_count(brain, "USA", "TOP3000", 1, "pv-price-volume") is None


def test_field_count_non_200_is_an_error():
    brain = FakeBrain([Resp(429, {})])
    assert _get_field_count(brain, "USA", "TOP3000", 1, "pv-price-volume") is None


def test_field_count_unparseable_body_is_an_error():
    brain = FakeBrain([Resp(200, ValueError("no json"))])
    assert _get_field_count(brain, "USA", "TOP3000", 1, "pv-price-volume") is None


# ── _paginate_fields ──────────────────────────────────────────────


def test_paginate_complete_when_every_page_arrives():
    brain = FakeBrain(
        [
            Resp(200, {"results": [_field("a"), _field("b")], "count": 3}),
            Resp(200, {"results": [_field("c")], "count": 3}),
        ]
    )
    fields, complete = _paginate_fields(brain, "USA", "TOP3000", 1, "pv-price-volume", 3)
    assert [f["id"] for f in fields] == ["a", "b", "c"]
    assert complete is True


def test_paginate_incomplete_on_400():
    brain = FakeBrain([Resp(400, {})])
    fields, complete = _paginate_fields(brain, "USA", "TOP3000", 1, "pv-price-volume", 500)
    assert fields == []
    assert complete is False


def test_paginate_incomplete_on_429_after_retries():
    """The thumbnail: a 429 after the session's retries truncated the walk."""
    brain = FakeBrain([Resp(200, {"results": [_field("a")]}), Resp(429, {})])
    fields, complete = _paginate_fields(brain, "USA", "TOP3000", 1, "pv-price-volume", 2)
    assert [f["id"] for f in fields] == ["a"]
    assert complete is False


def test_paginate_incomplete_on_empty_page_before_count():
    brain = FakeBrain([Resp(200, {"results": []})])
    fields, complete = _paginate_fields(brain, "USA", "TOP3000", 1, "pv-price-volume", 5)
    assert fields == []
    assert complete is False
