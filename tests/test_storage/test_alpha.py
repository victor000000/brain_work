"""store_alpha — basic insert + sparse data + high-quality flag."""

from storage.store_alpha import store_alpha
from tests.test_storage.conftest import alpha_data, conn, settings


def test_store_alpha():
    c = conn()
    store_alpha(c, "sim1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data())
    row = c.execute("SELECT * FROM alpha_results WHERE alpha_id='test123'").fetchone()
    assert row is not None
    assert row[0] == "test123"


def test_store_alpha_high_quality_flag():
    c = conn()
    data = alpha_data()
    data["is"]["sharpe"] = 2.0
    data["test"]["sharpe"] = 1.0
    store_alpha(c, "sim1", "rank(close)", "USA", "TOP3000", 1, settings(), data)
    row = c.execute("SELECT is_sharpe FROM alpha_results WHERE alpha_id='test123'").fetchone()
    assert row[0] == 2.0


def test_store_alpha_missing_fields():
    c = conn()
    data = {"id": "sparse", "status": "COMPLETE"}
    store_alpha(c, "sim1", "rank(x)", "EUR", "TOP2500", 1, settings(), data)
    row = c.execute("SELECT * FROM alpha_results WHERE alpha_id='sparse'").fetchone()
    assert row is not None
