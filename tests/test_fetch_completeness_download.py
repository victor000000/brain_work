"""A truncated region fetch must not be recorded as downloaded.

`--resume` skips combos present in download_log, so a partial fetch marked
complete is never retried.
"""

import pytest

from download.db_schema import init_db, is_downloaded
from download.fetch_fields import _download_region_fields
from tests.test_fetch_completeness_helpers import FakeBrain, Resp, _field


@pytest.fixture
def conn(tmp_path):
    c = init_db(str(tmp_path / "dl.db"))
    yield c
    c.close()


# ── _download_region_fields end-to-end ────────────────────────────


def test_incomplete_fetch_is_not_marked_downloaded(conn):
    brain = FakeBrain([Resp(200, {"count": 3}), Resp(429, {})])
    added, _skipped = _download_region_fields(brain, conn, [{"id": "pv-price-volume"}], "USA", "TOP3000", 1)
    assert added == 0
    assert not is_downloaded(conn, "USA", "TOP3000", 1, "pv-price-volume")


def test_incomplete_fetch_keeps_the_partial_rows(conn):
    brain = FakeBrain([Resp(200, {"count": 2}), Resp(200, {"results": [_field("a")]}), Resp(503, {})])
    _download_region_fields(brain, conn, [{"id": "pv-price-volume"}], "USA", "TOP3000", 1)
    assert conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0] == 1
    assert not is_downloaded(conn, "USA", "TOP3000", 1, "pv-price-volume")


def test_complete_fetch_is_marked_downloaded(conn):
    brain = FakeBrain([Resp(200, {"count": 1}), Resp(200, {"results": [_field("a")], "count": 1})])
    _download_region_fields(brain, conn, [{"id": "pv-price-volume"}], "USA", "TOP3000", 1)
    assert is_downloaded(conn, "USA", "TOP3000", 1, "pv-price-volume")


def test_malformed_count_is_not_marked_as_zero_fields(conn):
    brain = FakeBrain([Resp(200, ["nope"])])
    _download_region_fields(brain, conn, [{"id": "pv-price-volume"}], "USA", "TOP3000", 1)
    assert not is_downloaded(conn, "USA", "TOP3000", 1, "pv-price-volume")
    assert conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0] == 0


# ── scope filter at the write path ────────────────────────────────


def test_out_of_scope_subcategory_is_never_fetched_or_logged(conn):
    brain = FakeBrain([])  # any API call would raise IndexError
    added, skipped = _download_region_fields(
        brain, conn, [{"id": "model-technical"}, {"id": "news-news"}], "USA", "TOP3000", 1
    )
    assert (added, skipped) == (0, 0)
    assert brain.calls == []
    assert conn.execute("SELECT COUNT(*) FROM download_log").fetchone()[0] == 0


def test_in_scope_child_subcategory_is_fetched(conn):
    brain = FakeBrain([Resp(200, {"count": 1}), Resp(200, {"results": [_field("rel", sub="pv-relationship")]})])
    _download_region_fields(brain, conn, [{"id": "pv-relationship"}], "USA", "TOP3000", 1)
    assert is_downloaded(conn, "USA", "TOP3000", 1, "pv-relationship")


def test_download_log_never_gains_out_of_scope_rows(conn):
    """A mixed list: only the pv/option entries may reach the API or the log."""
    brain = FakeBrain([Resp(200, {"count": 1}), Resp(200, {"results": [_field("a")]})])
    _download_region_fields(
        brain,
        conn,
        [{"id": "fundamental-data"}, {"id": "pv-price-volume"}, {"id": "sentiment-sentiment"}],
        "USA",
        "TOP3000",
        1,
    )
    rows = [r[0] for r in conn.execute("SELECT subcategory_id FROM download_log")]
    assert rows == ["pv-price-volume"]
