"""Forum-mined template pool: expression draws and corpus provenance."""

import json
import random

from generator import template_source as ts
from tests import test_template_source_helpers as helpers
from tests.test_template_source_helpers import FIELDS, OPS, _clear_pool  # noqa: F401

# Bound here rather than imported by name: a direct import of `corpus` would be
# shadowed by the test parameters of the same name (ruff F811).
corpus = helpers.corpus


def test_next_expression_is_always_valid(corpus):
    rng = random.Random(4)
    got = 0
    for _ in range(40):
        expr = ts.next_expression(FIELDS, rng, OPS, corpus)
        if expr is None:
            continue
        got += 1
        assert "{" not in expr and "}" not in expr
        assert expr.count("(") == expr.count(")")
    assert got > 0


def test_next_expression_returns_none_on_empty_pool(tmp_path):
    assert ts.next_expression(FIELDS, random.Random(1), OPS, str(tmp_path / "no.json")) is None


def test_next_expression_returns_none_with_no_fields(corpus):
    assert ts.next_expression([], random.Random(1), OPS, corpus) is None


def test_next_expression_returns_none_for_an_invented_operator_pool(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps([{"skeleton": "totally_made_up({f})", "fillable_from_pv_option": True}]))
    assert ts.next_expression(FIELDS, random.Random(1), OPS, str(path)) is None


def test_next_expression_records_corpus_provenance(corpus):
    """A filled pool expression carries its corpus into template tracking.

    Without this the pool path recorded nothing, so `identify_template` fell
    through to the built-in regex signatures and stored every template-derived
    alpha as `unknown`.
    """
    from generator.weighted_selection import lookup_expr_template

    expr = ts.next_expression(FIELDS, random.Random(4), OPS, corpus)
    assert expr is not None
    assert lookup_expr_template(expr) == "pool:t"
    # Consumed on read: the second lookup must not resurrect the entry.
    assert lookup_expr_template(expr) is None


def test_a_small_corpus_is_not_drowned_by_a_large_one(monkeypatch):
    """The pool pick weights corpora, so `proven` is reachable.

    A flat draw is uniform over skeletons, which is the wrong unit when the
    corpora differ by two orders of magnitude: the four `proven` shapes sit in
    a pool of 519, so a flat draw reached them 4/519 of the time — measured
    2026-10-09, **0 of 1,948 alphas**. Weighting each corpus by sqrt(size)
    gives the small ones a share they can be measured on while leaving the
    community corpus dominant.

    This asserts the **size** term alone, so the measured-yield multipliers
    (`generator/corpus_prior.py`) must be off. They are module state that any
    test calling `load_corpus_prior` leaves behind, and the live explorer sets
    them on every batch — with `proven x2.58` loaded, `proven`'s share here is
    over the sqrt share the assertion below pins. That is how this test failed
    3,900 tests into a full run while passing in isolation: order dependence,
    not a weighting bug.
    """
    import math

    import generator.corpus_prior as corpus_prior
    from generator.template_source_pick import _corpus_row_weights

    monkeypatch.setattr(corpus_prior, "_multipliers", {})

    pool = [{"corpus": "forum"}] * 500 + [{"corpus": "proven"}] * 4 + [{"corpus": "curated"}] * 3
    weights = _corpus_row_weights(pool)
    share = {}
    for row, w in zip(pool, weights, strict=True):
        share[row["corpus"]] = share.get(row["corpus"], 0.0) + w
    total = sum(share.values())
    assert math.isclose(share["forum"] / total, math.sqrt(500) / (math.sqrt(500) + math.sqrt(4) + math.sqrt(3)))
    # forum stays dominant; proven is no longer a rounding error.
    assert share["forum"] / total > 0.7
    assert share["proven"] / total > 0.05


def test_weights_are_per_row_not_per_corpus():
    """Summing a corpus' rows gives its share, whatever its size."""
    from generator.template_source_pick import _corpus_row_weights

    pool = [{"corpus": "a"}] * 100 + [{"corpus": "b"}] * 1
    w = _corpus_row_weights(pool)
    assert all(x == w[0] for x in w[:100])
    assert w[100] > w[0], "the lone b row must outweigh a single a row"
