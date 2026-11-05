"""Fields the platform has never simulated into an alpha, from our own results.

The rule is a pool filter scored on recorded outcomes, not on names: a field
with >= MIN_USES child simulations in the window and zero alphas is dead, and so
is a field whose *family* — the id with every digit run masked — has
>= MIN_FAMILY_USES and zero. The family level exists because the `_t_` variant
family shares ~3.5 draws per field and 151 draws in total, so no single member
carries the evidence.
"""

import time

from core.db import connect
from generator import field_dead
from generator.field_dead import dead_fields, family_of


def make_conn(children=(), fields=("close", "volume", "pv20_returns4_t_1662")):
    """A minimal DB: `simulations` rows as (expression, alpha_id) plus a vocab."""
    conn = connect(":memory:")
    conn.execute(
        """
        CREATE TABLE simulations (
            sim_id TEXT, parent_id TEXT, expression TEXT, alpha_id TEXT, completed_at TEXT
        )
        """
    )
    conn.execute("CREATE TABLE data_fields (id TEXT)")
    conn.executemany("INSERT INTO data_fields VALUES (?)", [(f,) for f in fields])
    for i, (expr, alpha) in enumerate(children):
        conn.execute(
            "INSERT INTO simulations VALUES (?,?,?,?,?)",
            (f"s{i}", "parent", expr, alpha, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
        )
    conn.commit()
    return conn


def test_family_of_masks_every_digit_run():
    assert family_of("pv20_returns4_t_1663") == "pv20_returns#_t_#"
    # The dataset number is not a variant suffix: pv20 and pv37 stay apart.
    assert family_of("pv20_close_9") != family_of("pv37_close_9")
    assert family_of("close") == "close"
    assert family_of("pv37_close_12") == family_of("pv37_close_13")


def test_a_field_with_three_draws_and_no_alpha_is_dead():
    conn = make_conn([("rank(volume)", None)] * 3)
    assert "volume" in dead_fields(conn)


def test_a_field_with_one_alpha_is_not():
    conn = make_conn([("rank(volume)", None), ("rank(volume)", None), ("rank(volume)", "Abc123")])
    assert "volume" not in dead_fields(conn)


def test_two_draws_are_not_enough_on_their_own():
    """Three is the floor; below it a coin flip would do the same thing."""
    conn = make_conn([("rank(volume)", None)] * 2)
    assert "volume" not in dead_fields(conn)


def test_a_family_pools_its_members_evidence():
    """The `_t_` shape: 43 fields, ~3.5 draws each, 151 draws and no alpha."""
    fields = [f"pv20_returns4_t_{n}" for n in range(4)]
    children = [(f"rank({f})", None) for f in fields for _ in range(3)]
    conn = make_conn(children, fields=fields)
    dead = dead_fields(conn)
    assert set(dead) == set(fields), "each member is dead on its family's record"


def test_a_working_sibling_keeps_its_family_in_the_pool():
    """Each field is under the per-field bar, so only the family clause could fire."""
    fields = [f"pv20_returns4_t_{n}" for n in range(4)]
    children = [(f"rank({f})", None) for f in fields for _ in range(2)]
    children.append(("rank(pv20_returns4_t_3)", "Abc123"))  # one survives
    children.append(("rank(pv20_returns4_t_3)", "Abc124"))
    children.append(("rank(pv20_returns4_t_3)", "Abc125"))
    conn = make_conn(children, fields=fields)
    assert dead_fields(conn) == set(), "the family has alphas, so nothing in it is dead"


def test_a_missing_simulations_table_is_empty_not_an_error():
    """A fresh schema must leave generation exactly as it was."""
    conn = connect(":memory:")
    conn.execute("CREATE TABLE data_fields (id TEXT)")
    assert dead_fields(conn) == set()


def test_the_cache_recomputes_only_when_stale(monkeypatch):
    field_dead.reset_cache()
    conn = make_conn([("rank(volume)", None)] * 3)
    first = field_dead.cached_dead_fields(conn)
    assert "volume" in first
    conn.execute(
        "INSERT INTO simulations VALUES ('x','parent','rank(volume)','Abc123',?)", (time.strftime("%Y-%m-%d"),)
    )
    conn.commit()
    assert field_dead.cached_dead_fields(conn) == first, "served from cache"
    # Past the cache window the new alpha is seen.
    assert field_dead.cached_dead_fields(conn, now=time.time() + field_dead.CACHE_SEC + 1) == set()
    field_dead.reset_cache()
