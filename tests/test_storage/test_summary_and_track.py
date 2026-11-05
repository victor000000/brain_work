"""print_summary smoke test + track_operator_usage."""

from storage.store_alpha import store_alpha
from storage.store_sim import store_sim
from storage.summary import print_summary
from storage.track_ops import track_operator_usage
from tests.test_storage.conftest import alpha_data, conn, settings


def test_summary(_capsys=None):
    c = conn()
    store_alpha(c, "s1", "rank(x)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))
    store_sim(c, "s1", "p1", 0, "rank(x)", "USA", "TOP3000", 1, "COMPLETE", "a1", None, settings(), "now")
    print_summary(c)


def test_track_operator_usage():
    c = conn()
    track_operator_usage(c, "rank(ts_delta(close, 5))", "USA")
    rows = c.execute("SELECT * FROM operator_usage").fetchall()
    ops = {r[0] for r in rows}
    assert "rank" in ops
    assert "ts_delta" in ops
