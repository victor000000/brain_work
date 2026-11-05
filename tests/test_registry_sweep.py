"""The registry sweep: convention dispatch, and what it reports as data.

`render` dispatches on `registry.template_uses_pool`, which reads the registry
list — so the tests inject the dispatch rather than registering fake templates.
That dependency is the point: calling a `(fields, rng)` template the two-field
way raises `'str' object has no attribute 'choice'` inside the *template*, and
the 2026-10-11 sweep read that class of failure as 9,750 invalid renders.

`sweep_cell` returning counts rather than printing them is what makes the sweep
testable without a database.
"""

import random

import tools.registry_sweep as sweep
from tools.registry_sweep import render, sweep_cell

FIELDS = ["close", "volume", "cap"]


def _pool_template(fields, rng):
    return f"rank({rng.choice(fields)})"


def _two_field_template(f1, f2):
    return f"ts_corr({f1},{f2},20)"


def _fixed_pool(fields, rng):
    return "rank(close)"


def _fixed_two(f1, f2):
    return "ts_corr(close,cap,20)"


def _bad_pool(fields, rng):
    return "rank(volume)"  # the stub validator rejects anything reading volume


def _empty_pool(fields, rng):
    return None


POOL_TEMPLATES = {_pool_template, _fixed_pool, _bad_pool, _empty_pool}


def _stub_validate(expr, field_pool, known_ops, vector_fields, group_fields):
    return "unknown field(s): volume" if "volume" in expr else None


def test_render_dispatches_by_convention(monkeypatch):
    """A pool template gets `(fields, rng)`; a two-field one gets two names."""
    monkeypatch.setattr(sweep, "template_uses_pool", lambda fn: fn in POOL_TEMPLATES)

    expr = render(_pool_template, FIELDS, random.Random(1))
    assert expr.startswith("rank(") and expr.endswith(")")

    seen = set()
    for seed in range(6):
        expr = render(_two_field_template, FIELDS, random.Random(seed))
        assert expr.startswith("ts_corr(")
        seen.add(expr)
    assert len(seen) > 1, "a two-field template must be drawn fresh, not handed the pool"


def test_render_returns_none_when_two_field_convention_lacks_fields():
    assert render(_two_field_template, ["close"], random.Random(1)) is None
    assert render(_two_field_template, [], random.Random(1)) is None


def test_sweep_cell_counts_reports_invalid_and_never(monkeypatch):
    monkeypatch.setattr(sweep, "template_uses_pool", lambda fn: fn in POOL_TEMPLATES)
    templates = [(_fixed_pool, ["rank"]), (_fixed_two, ["ts_corr"]), (_bad_pool, ["rank"]), (_empty_pool, ["rank"])]
    count, invalid, never = sweep_cell(templates, FIELDS, set(), set(), set(), renders=4, validate=_stub_validate)
    assert count == 12, "three templates emit four renders each; the fourth emits none"
    assert [name for name, _problem, _expr in invalid] == ["_bad_pool"] * 4
    assert never == ["_empty_pool"]
    assert all(expr == "rank(volume)" for _n, _p, expr in invalid)
