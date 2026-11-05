"""find_group_unit_offenders — scan failed sims for Unit[Group:1] errors."""

from core.db import connect
from download.blacklist_group_unit import find_group_unit_offenders
from tests.test_blacklist_group_unit.conftest import make_test_conn


def test_find_offenders_basic():
    """group_id rows from failing sims are returned; price/CHN included as collateral."""
    conn = make_test_conn()
    offenders = find_group_unit_offenders(conn)
    assert ("group_id", "USA") in offenders
    assert ("group_id", "CHN") in offenders
    assert ("price", "CHN") in offenders
    assert ("price", "USA") not in offenders


def test_find_offenders_empty_db():
    """No simulations rows -> empty result."""
    conn = connect(":memory:")
    conn.executescript("""
        CREATE TABLE data_fields (id TEXT, type TEXT, region TEXT, description TEXT);
        CREATE TABLE simulations (sim_id TEXT, expression TEXT, region TEXT,
                                  status TEXT, error_message TEXT);
    """)
    assert find_group_unit_offenders(conn) == []


def test_find_offenders_only_unit_group_errors():
    """Other ERROR messages are ignored - only Unit[Group:1] is targeted."""
    conn = make_test_conn()
    conn.execute(
        "INSERT INTO simulations VALUES (?, ?, ?, ?, ?)",
        ("s4", "rank(unrelated_field)", "USA", "ERROR", "Some other unrelated error"),
    )
    conn.execute(
        "INSERT INTO data_fields VALUES (?, ?, ?, ?)",
        ("unrelated_field", "MATRIX", "USA", "desc"),
    )
    offenders = find_group_unit_offenders(conn)
    assert ("unrelated_field", "USA") not in offenders
