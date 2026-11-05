"""Settings controls retain their own labels across completion order/restart."""

import json

import pytest

from generator.weighted_selection import record_expr_template
from storage.probe_attribution import probe_template
from storage.store_alpha import store_alpha
from tests.test_storage.conftest import alpha_data, conn, settings


@pytest.fixture
def db():
    c = conn()
    yield c
    c.close()


def add_probe(c, parent, expressions, tags):
    c.execute("INSERT INTO simulations (sim_id) VALUES (?)", (parent,))
    c.execute(
        "INSERT INTO probe_batches (probe_id,parent_id,expressions,template_tags,settings,created_at) "
        "VALUES (?,?,?,?,?,'2026-10-19 08:00:00 UTC')",
        (parent, parent, json.dumps(expressions), json.dumps(tags), "{}"),
    )


def test_same_expression_settings_controls_ignore_overwritten_ledger(db):
    expr = "rank(close)"
    add_probe(db, "p8", [expr], ["probe:decay8"])
    add_probe(db, "p15", [expr], ["probe:decay15"])
    record_expr_template(expr, "probe:decay15")
    # Complete the earlier submission after the expression ledger changed.
    for parent, aid, decay in [("p15", "a15", 15), ("p8", "a8", 8)]:
        store_alpha(db, parent, expr, "USA", "TOP3000", 1, {**settings(), "decay": decay}, alpha_data(aid))
    assert db.execute("SELECT alpha_id,template FROM alpha_results ORDER BY alpha_id").fetchall() == [
        ("a15", "probe:decay15"),
        ("a8", "probe:decay8"),
    ]
    assert db.execute("SELECT alpha_id,template_name FROM template_performance ORDER BY alpha_id").fetchall() == [
        ("a15", "probe:decay15"),
        ("a8", "probe:decay8"),
    ]


def test_child_uses_exact_expression_in_its_parent_without_ledger(db):
    add_probe(db, "parent", ["rank(open)", "rank(close)"], ["probe:open", "probe:close"])
    db.execute("INSERT INTO simulations (sim_id,parent_id) VALUES ('child','parent')")
    assert probe_template(db, "child", "rank(close)") == "probe:close"
    assert probe_template(db, "parent", "rank(open)") == "probe:open"


def test_ordinary_simulation_has_no_probe_override(db):
    db.execute("INSERT INTO simulations (sim_id) VALUES ('ordinary')")
    assert probe_template(db, "ordinary", "rank(close)") is None
    assert probe_template(db, "missing", "rank(close)") is None


@pytest.mark.parametrize("tags", [[], ["a", "b"], [None], [""]])
def test_malformed_probe_does_not_borrow_another_controls_tag(db, tags):
    add_probe(db, "parent", ["rank(close)"], tags)
    assert probe_template(db, "parent", "rank(close)") == "unknown"
