"""store_sim — basic submission row + error_records sidecar table."""

from storage.store_sim import store_sim
from tests.test_storage.conftest import conn, settings


def test_store_sim():
    c = conn()
    store_sim(
        c,
        "sim1",
        None,
        0,
        "rank(x)",
        "USA",
        "TOP3000",
        1,
        "SUBMITTED",
        None,
        None,
        settings(),
        "2026-04-09",
    )
    row = c.execute("SELECT * FROM simulations WHERE sim_id='sim1'").fetchone()
    assert row is not None
    assert row[7] == "SUBMITTED"


def test_store_sim_error_records():
    c = conn()
    store_sim(
        c,
        "sim2",
        "p1",
        1,
        "bad(x)",
        "EUR",
        "TOP2500",
        1,
        "ERROR",
        None,
        "division by zero",
        settings(),
        "2026-04-09",
    )
    err = c.execute("SELECT * FROM sim_errors").fetchone()
    assert err is not None
    assert "division" in err[3]
