"""Per-expression selection out of the loaded template pool.

Split out of `generator/template_source.py`, which re-exports these names so
`from generator import template_source as ts` keeps seeing them.
"""

from __future__ import annotations

import collections
import math
import random

from generator.corpus_prior import corpus_multiplier
from generator.template_fill import FILL_ATTEMPTS, fill_skeleton, filled_expression_problem, slot_count
from generator.template_source_pool import load_pool
from generator.validate import load_operator_names
from generator.weighted_selection import record_expr_template


def _corpus_row_weights(pool) -> list[float]:
    """Per-skeleton draw weights, so each corpus' share goes as sqrt(its size).

    Returned per *row*, i.e. already divided within each corpus, so summing the
    rows of a corpus gives that corpus' share regardless of how many skeletons
    it holds. A corpus missing a label is treated as its own group keyed by
    None, which keeps a caller that bypasses `load_pool` from crashing.

    Each corpus' share is then scaled by its measured yield multiplier
    (`generator/corpus_prior.py`). Size alone models how much text a corpus
    contributed and not whether its shapes work: `forum` holds 66% of the pool
    and reaches the sharpe floor at 0.25% of its alphas, `proven` holds 21% and
    reaches it at 2.04%. Until `load_corpus_prior` has run — or with
    `BRAIN_CORPUS_PRIOR=0` — every multiplier is 1.0 and this is the pure size
    weighting it has always been.
    """
    sizes = collections.Counter(t.get("corpus") for t in pool)
    per_corpus = {corpus: math.sqrt(n) / n for corpus, n in sizes.items()}
    return [per_corpus[t.get("corpus")] * corpus_multiplier(t.get("corpus")) for t in pool]


def next_expression(
    fields,
    rng: random.Random,
    known_operators,
    path=None,
    target_fields=None,
    vector_fields=None,
    group_fields=None,
) -> str | None:
    """One validated expression from the template pool, or None.

    `target_fields` supplies the first slot, so the expression lands in the
    pyramid the explorer targeted — the same guarantee `pick_matrix` gives
    built-in templates. A slotless skeleton cannot carry a target field at all,
    so when `target_fields` is supplied it is skipped rather than spending the
    batch's template share on an expression that ignores the target.

    `vector_fields`/`group_fields` are the typed pools, used to reject fillings
    that put a MATRIX field where a VECTOR or GROUP is required (see
    `template_fill.type_violation`).

    Returns None rather than an invalid expression — the caller falls back to
    its own generator, so a poor corpus degrades output instead of breaking it.
    """
    if not fields:
        return None
    pool = load_pool(fields, known_operators, path)
    if not pool:
        return None

    if target_fields:
        pool = [t for t in pool if slot_count(t["skeleton"]) > 0]
        if not pool:
            return None

    # Sample without replacement: a skeleton that always violates (a `vec_*`
    # template in a MATRIX pool cannot be filled any other way) is not retried
    # at the expense of candidates that could succeed.
    #
    # Weighted by corpus, so a small one is not drowned by a large one. A flat
    # pick is uniform over *skeletons*, and that is the wrong unit when the
    # corpora differ by two orders of magnitude: the four `proven` shapes sit
    # in a pool of 519, so a flat draw reaches them 4/519 of the time — at a
    # 10% template mix and ~400 alphas/hour that is one alpha every 20 minutes,
    # and measured 2026-10-09 it was **0 of 1,948**. A corpus's share goes as
    # the square root of its usable size (diminishing returns to size, the
    # standard choice): forum 500 -> 75% of draws, cnhkmcp 13 -> 12%, proven
    # 4 -> 6.7%, curated 3 -> 5.7%. That leaves the community corpus dominant,
    # which matters because it is the only source of shapes to be
    # *uncorrelated* with, while giving `proven` enough traffic (~65 a day) to
    # measure — which is all the evidence for it supports: its four shapes were
    # chosen because they produced accepted alphas, so their record is
    # retrospective and not a yield.
    #
    # That traffic did get `proven` measured, and the answer moved the weights
    # again: it reaches the sharpe floor at 2.04% of its alphas against 0.25%
    # for `forum` — see `_corpus_row_weights` and `generator/corpus_prior.py`.
    row_weights = _corpus_row_weights(pool)
    remaining = list(range(len(pool)))
    for _ in range(min(len(pool), FILL_ATTEMPTS)):
        total = sum(row_weights[i] for i in remaining)
        target, acc = rng.random() * total, 0.0
        # Default keeps a float-rounding miss from raising IndexError.
        chosen = remaining[-1]
        for idx in remaining:
            acc += row_weights[idx]
            if target <= acc:
                chosen = idx
                break
        remaining.remove(chosen)
        template = pool[chosen]
        expr = fill_skeleton(
            template["skeleton"],
            fields,
            rng,
            first_pool=target_fields,
            group_fields=group_fields,
            vector_fields=vector_fields,
            slot_bindings=template.get("slot_bindings"),
            example=template.get("example"),
        )
        if expr and filled_expression_problem(expr, fields, known_operators, vector_fields, group_fields) is None:
            # Record provenance for the caller's storage path. The map is keyed
            # by expression string and consumed on read, so every path that
            # discards a candidate releases it (see random_generator).
            record_expr_template(expr, f"pool:{template['corpus']}")
            return expr
    return None


def target_pool(cache, category) -> list:
    """MATRIX fields belonging to `category`, for pyramid targeting.

    Empty when the category is unknown or has no loaded datasets, which
    `fill_skeleton` treats as no preference.
    """
    if not category:
        return []
    datasets = getattr(cache, "datasets_by_category", {}).get(category, [])
    return [f for ds in datasets for f in cache.matrix_by_dataset.get(ds, [])]


def operators_from(conn) -> set[str]:
    """Operator allowlist for this database."""
    return load_operator_names(conn)
