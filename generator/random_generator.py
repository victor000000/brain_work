"""Random Alpha Generator — weighted by operator coverage.

5 economic themes: momentum, reversion, relative, transform, conditional.
Multi-field combos for complex multi-factor alphas.
Weights are dynamic — less-used operators get higher probability.

A share of each batch comes from templates mined off the community forum
(`generator/template_source.py`), filled with pv/option fields at generation
time. Templates whose output fails validation are discarded, so a batch never
contains an expression that would waste a simulation on a syntax error.
Set BRAIN_TEMPLATE_MIX=0 to use only the curated built-in templates.
"""

import os
import random

from core.log import get_file_logger
from generator.diversity_weights import load_diversity_weights
from generator.field_picker import load_all_fields
from generator.field_picker_matrix import pick_matrix
from generator.random_generator_build import _make_2field_expression, _make_3field, _make_4field, _make_5field
from generator.random_generator_pools import prepare_pools, template_candidate
from generator.random_generator_rounds import GENERATION_ROUNDS, collect_valid  # noqa: F401
from generator.sign_policy import load_sign_policy, maybe_negate
from generator.weighted_selection import load_usage

glog = get_file_logger("generator")

# One Random instance for the module: candidate source selection, template
# filling and pool sampling all use it (not the random module), so those are
# reproducible under BRAIN_RNG_SEED. The built-in builders draw from the global
# random module, so their internals stay unseeded.
_RNG = random.Random(os.environ.get("BRAIN_RNG_SEED") or None)


def generate_expressions(conn, region, delay, universe, count, neutralization=None):
    """Generate expressions with dynamic operator-coverage weighting.

    `neutralization` is pre-picked by the explorer so the cell key
    (region, universe, delay, neutralization) is fully known at template-pick
    time. When None, the cell_context is omitted (callers that don't want
    posterior weighting can pass None).

    Every candidate — built-in or template-derived — is validated with
    `filled_expression_problem` (syntax, operator allowlist, field membership,
    argument types) before it is returned, and dropped (with a warning) when it
    fails. If that leaves fewer than `count`, the generator runs again, up to
    GENERATION_ROUNDS passes.
    """
    load_usage(conn)
    load_diversity_weights(conn)
    load_all_fields(conn, region, delay, universe)
    load_sign_policy(conn)

    if len(pick_matrix(count=2)) < 2:
        glog.warning("Too few fields for %s/%s/d%d", region, universe, delay)
        return []

    cell_context = (region, universe, delay, neutralization) if neutralization is not None else None
    cache, field_pool, vector_fields, group_fields, known_operators, mix = prepare_pools(conn)
    stats = {"errors": 0}

    def batch(n: int, allow_templates: bool = True) -> list[str]:
        """Raw candidates — validated by the caller, not here.

        `allow_templates=False` is used after a round produced nothing valid:
        if the template path is the broken one, retrying it would exhaust the
        bounded rounds without ever topping the batch up from the built-ins.
        """
        out: list[str] = []
        for _ in range(n * 20):
            if len(out) >= n:
                break
            try:
                expr = None
                if mix and allow_templates and _RNG.random() < mix:
                    expr = template_candidate(field_pool, _RNG, known_operators, cache, vector_fields, group_fields)
                    # A poor corpus returns None; fall through to the built-ins
                    # rather than burning the iteration.
                if not expr:
                    r = _RNG.random()
                    if r < 0.05:
                        expr = _make_5field(cell_context=cell_context)
                    elif r < 0.20:
                        expr = _make_4field(cell_context=cell_context)
                    elif r < 0.55:
                        expr = _make_3field(cell_context=cell_context)
                    else:
                        expr = _make_2field_expression(cell_context=cell_context)
                if expr:
                    # Orientation is applied here, before the caller validates
                    # and records, so provenance stays keyed by the string that
                    # is actually emitted. A cell whose outcomes say its signals
                    # arrive inverted gets a share of its candidates negated —
                    # see generator/sign_policy.py for the measurement.
                    out.append(maybe_negate(expr, _RNG, region))
            except Exception as e:
                stats["errors"] += 1
                glog.debug("Template error: %s", e)
        return out

    pools = (field_pool, known_operators, vector_fields, group_fields)
    return collect_valid(batch, pools, count, stats, region, universe, delay)
