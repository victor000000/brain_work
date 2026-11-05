"""F6 cache-holder tests for UsageState — reset, expr-template recording, weights."""

import math

import generator.weighted_selection as ws


def test_usage_state_reset():
    s = ws.UsageState()
    s.usage_cache = {"rank": 100}
    s.expr_templates = {"rank(x)": "tmpl_a"}
    s.reset()
    assert s.usage_cache == {}
    assert s.expr_templates == {}


def test_record_and_lookup_expr_template():
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        ws.record_expr_template("rank(x)", "tmpl_a")
        assert ws.lookup_expr_template("rank(x)") == "tmpl_a"
        # lookup consumes — second call returns None.
        assert ws.lookup_expr_template("rank(x)") is None
    finally:
        ws.set_state(ws.UsageState())


def test_expr_templates_is_fifo_capped():
    """Expressions that are never looked up (duplicates, validation failures,
    failed submissions) must not grow the map for the process's lifetime."""
    from generator.weighted_selection.state import MAX_TRACKED_EXPRESSIONS

    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        for i in range(MAX_TRACKED_EXPRESSIONS + 10):
            ws.record_expr_template(f"expr_{i}", "tmpl")
        assert len(fresh.expr_templates) == MAX_TRACKED_EXPRESSIONS
        # Oldest evicted, newest kept.
        assert ws.lookup_expr_template("expr_0") is None
        assert ws.lookup_expr_template(f"expr_{MAX_TRACKED_EXPRESSIONS + 9}") == "tmpl"
    finally:
        ws.set_state(ws.UsageState())


def test_record_expr_template_ignores_none():
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        ws.record_expr_template(None, "tmpl")
        assert fresh.expr_templates == {}
    finally:
        ws.set_state(ws.UsageState())


def test_lookup_releases_the_entry():
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        ws.record_expr_template("rank(x)", "tmpl")
        assert ws.lookup_expr_template("rank(x)") == "tmpl"
        assert fresh.expr_templates == {}
    finally:
        ws.set_state(ws.UsageState())


def test_get_weight_uses_state_cache():
    fresh = ws.UsageState()
    fresh.usage_cache = {"rank": 100, "signed_power": 0}
    ws.set_state(fresh)
    try:
        # min usage = 0 → weight = 1.0.
        assert ws.get_weight(["rank", "signed_power"]) == 1.0
        # min usage = 100 → weight = 1/(1 + log1p(100)).
        assert abs(ws.get_weight(["rank"]) - 1.0 / (1 + math.log1p(100))) < 1e-9
    finally:
        ws.set_state(ws.UsageState())


def test_weighted_choice_returns_function_and_name():
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:

        def t1(a, b):
            return f"t1({a},{b})"

        def t2(a, b):
            return f"t2({a},{b})"

        templates = [(t1, ["op1"]), (t2, ["op2"])]
        fn, name = ws.weighted_choice(templates)
        assert fn in (t1, t2)
        assert name in ("t1", "t2")
        assert callable(fn)
    finally:
        ws.set_state(ws.UsageState())


def test_the_weight_range_is_bounded():
    """The coverage weight has to bound its own range.

    With the linear form and the real counts (`rank` alone at 155,700), 21 of
    the registry's 38 templates fell below 1e-4 and two took 95.6% of the
    weight between them. Four of the starved ones — `ts_backfill_negmean`,
    `staleness_decay`, `scale_rank_zscore`, `power_ratio`, the shapes with no
    correlation failures in 495 checked alphas — had produced no alphas at all
    since 2026-10-03.
    """
    fresh = ws.UsageState()
    fresh.usage_cache = {"rank": 155700, "ts_mean": 40022, "rare_op": 3}
    ws.set_state(fresh)
    try:
        common = ws.get_weight(["rank"])
        # Not ~1e-5: a template built from ubiquitous operators stays selectable.
        assert common > 0.05, common
        # Ordering survives — rare operators still outweigh common ones...
        assert ws.get_weight(["rare_op"]) > common
        # ...but the spread is bounded rather than 400,000:1.
        assert ws.get_weight(["rare_op"]) / common < 100
    finally:
        ws.set_state(ws.UsageState())


def test_peek_does_not_consume_the_entry():
    """`identify_template` peeks, so a constant expression stays attributed.

    The map is keyed by expression string and a slotless template emits the
    same string on every draw, so a consuming read gave the name to the first
    alpha of that shape and `unknown` to the rest. Consuming is still what
    `_release` needs, which is why both exist.
    """
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        ws.record_expr_template("(close - vwap) / vwap", "vwap_close_spread")
        assert ws.peek_expr_template("(close - vwap) / vwap") == "vwap_close_spread"
        # Still there for the next alpha of the same shape...
        assert ws.peek_expr_template("(close - vwap) / vwap") == "vwap_close_spread"
        # ...while a consuming lookup still removes it.
        assert ws.lookup_expr_template("(close - vwap) / vwap") == "vwap_close_spread"
        assert ws.peek_expr_template("(close - vwap) / vwap") is None
    finally:
        ws.set_state(ws.UsageState())
