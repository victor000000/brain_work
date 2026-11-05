"""Generator batching — candidate order and template attribution on dedup."""

from tests.conftest import open_prod_db


def test_batch_preserves_candidate_order(monkeypatch):
    """Candidates are returned in production order — `list(set(...))[:count]`
    reordered them nondeterministically and made reruns irreproducible."""
    from generator import random_generator as rg
    from generator import template_source

    conn = open_prod_db()
    monkeypatch.setattr(template_source, "template_mix", lambda: 0.0)
    pool = iter(["rank(close)", "rank(volume)", "rank(vwap)", "rank(cap)", "rank(returns)"])
    monkeypatch.setattr(rg, "_make_2field_expression", lambda cell_context=None: next(pool, None))
    monkeypatch.setattr(rg, "_make_3field", lambda cell_context=None: None)
    monkeypatch.setattr(rg, "_make_4field", lambda cell_context=None: None)
    monkeypatch.setattr(rg, "_make_5field", lambda cell_context=None: None)

    exprs = rg.generate_expressions(conn, "USA", 1, "TOP3000", 5)
    assert exprs == ["rank(close)", "rank(volume)", "rank(vwap)", "rank(cap)", "rank(returns)"]


def test_duplicate_does_not_release_a_kept_expressions_template_entry(monkeypatch):
    """Dedup discards a duplicate, but the identical string stays in the batch.

    The expression -> template map is keyed by string, so releasing the entry
    on the duplicate would strip the kept copy's generation-time attribution
    when storage consumes it (identify_template pops on first read).
    """
    from generator import random_generator as rg
    from generator import template_source
    from generator.weighted_selection import get_state, record_expr_template

    conn = open_prod_db()
    monkeypatch.setattr(template_source, "template_mix", lambda: 0.0)

    pool = iter(["rank(close)", "rank(close)", "rank(volume)", "rank(volume)", "rank(vwap)"])

    def fake(cell_context=None):
        expr = next(pool, None)
        if expr:
            # Mimic the real built-in path, which records before returning.
            record_expr_template(expr, "momentum_basic")
        return expr

    monkeypatch.setattr(rg, "_make_2field_expression", fake)
    monkeypatch.setattr(rg, "_make_3field", lambda cell_context=None: None)
    monkeypatch.setattr(rg, "_make_4field", lambda cell_context=None: None)
    monkeypatch.setattr(rg, "_make_5field", lambda cell_context=None: None)

    state = get_state()
    saved = dict(state.expr_templates)
    state.expr_templates.clear()
    try:
        exprs = rg.generate_expressions(conn, "USA", 1, "TOP3000", 2)
        entries = dict(state.expr_templates)
    finally:
        state.expr_templates.clear()
        state.expr_templates.update(saved)

    assert len(exprs) == 2, exprs
    assert exprs[0] == "rank(close)", exprs
    assert entries.get("rank(close)") == "momentum_basic", "kept expression lost its template attribution"


def test_a_cross_batch_duplicate_keeps_the_pending_attribution():
    """A constant expression recurs across batches while earlier copies are
    still awaiting storage; discarding the later copy must not evict the entry
    the earlier one still needs.

    `_recent` holds 2000 expressions and storage lags generation by a whole
    simulation, so a slotless template emitting `(close - vwap) / vwap` records
    the same key repeatedly with earlier copies still unstored. Releasing on
    the duplicate popped that key, and the regex fallback has no pattern for a
    pure-arithmetic expression — so the alphas landed in `template_performance`
    as `unknown`, a name nothing weights. This is the second half of the same
    hazard `test_duplicate_does_not_release_a_kept_expressions_template_entry`
    covers for a single call.
    """
    from generator import random_generator_rounds as rgr
    from generator.weighted_selection import get_state, record_expr_template

    expr = "(close - vwap) / vwap"
    state = get_state()
    saved_entries = dict(state.expr_templates)
    saved_recent, saved_set = list(rgr._recent), set(rgr._recent_set)
    state.expr_templates.clear()
    rgr._recent.clear()
    rgr._recent_set.clear()
    try:
        # An earlier batch emitted it, and its simulation has not landed yet.
        rgr._remember(expr)
        record_expr_template(expr, "vwap_close_spread")

        calls = []

        def batch(n, allow_templates=True):
            calls.append(allow_templates)
            # One sighting, which round 0 must reject as a duplicate, then
            # nothing — so the last round never gets to re-record it.
            return [expr] if len(calls) == 1 else []

        kept = rgr.collect_valid(batch, (["close", "vwap"], set(), [], []), 1, {"errors": 0}, "USA", "TOP3000", 0)
        # Read inside the try: the finally below restores the singleton, so an
        # assertion after it would inspect the restored state, not this run's.
        survived = state.expr_templates.get(expr)
    finally:
        state.expr_templates.clear()
        state.expr_templates.update(saved_entries)
        rgr._recent.clear()
        rgr._recent.extend(saved_recent)
        rgr._recent_set.clear()
        rgr._recent_set.update(saved_set)

    assert kept == [], "the duplicate should not have entered the batch"
    assert survived == "vwap_close_spread", "the pending copy lost the attribution it had not been stored with yet"
