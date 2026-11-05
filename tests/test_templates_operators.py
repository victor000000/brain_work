"""Every operator tag in the templates must be a valid BRAIN operator, and it
must be exactly what the template emits."""

import random

from generator.registry import ALL_TEMPLATES, template_uses_pool
from generator.validate import called_identifiers
from tests.test_templates_helpers import POOL

# Valid BRAIN operators (level=ALL)
VALID_OPS = {
    "abs",
    "and",
    "bucket",
    "days_from_last_change",
    "densify",
    "group_backfill",
    "group_cartesian_product",
    "group_mean",
    "group_neutralize",
    "group_rank",
    "group_scale",
    "group_std_dev",
    "group_zscore",
    "greater",
    "hump",
    "if_else",
    "inverse",
    "is_nan",
    "kth_element",
    "last_diff_value",
    "log",
    "max",
    "min",
    "normalize",
    "power",
    "quantile",
    "rank",
    "reverse",
    "scale",
    "sign",
    "signed_power",
    "sqrt",
    "tail",
    "trade_when",
    "ts_arg_max",
    "ts_arg_min",
    "ts_av_diff",
    "ts_backfill",
    "ts_corr",
    "ts_count_nans",
    "ts_covariance",
    "ts_decay_linear",
    "ts_delay",
    "ts_delta",
    "ts_ir",
    "ts_max_diff",
    "ts_mean",
    "ts_product",
    "ts_quantile",
    "ts_rank",
    "ts_regression",
    "ts_scale",
    "ts_std_dev",
    "ts_step",
    "ts_sum",
    "ts_target_tvr_decay",
    "ts_zscore",
    "vec_avg",
    "vec_sum",
    "winsorize",
    "zscore",
}


def test_template_operators_are_valid():
    """All operator tags in templates are valid BRAIN operators."""
    for fn, ops in ALL_TEMPLATES:
        for op in ops:
            assert op in VALID_OPS, f"{fn.__name__} has invalid op: {op}"


def test_template_operator_tags_match_the_expressions_they_emit():
    """A tag must list exactly the operators its template can emit.

    `weighted_selection.get_weight` takes the minimum recorded usage over the
    declared operators, so the tag is the template's statement of which
    operators it spends. An operator left out of the tag is never counted
    against it — measured 2026-10-09, `options_pcr_volume_gated` emitted
    `ts_delta` in 31 of its 40 recorded alphas (the PCR-less fallback, which
    every region but USA/IND takes) while declaring only `trade_when`/`rank`,
    so it kept their under-used weight on draws that mostly spent `ts_delta`.
    A tag op the template never emits is the same defect in reverse: it damps
    the template's weight against coverage it does not provide.

    Both pools are run because a template's operator set can depend on what
    the region's pool offers: the second has no options datafield, so the
    fallback branch above is exercised rather than assumed.
    """
    no_options = [f for f in POOL if "pcr" not in f.lower() and "put_call" not in f.lower()]
    for fn, declared in ALL_TEMPLATES:
        actual = set()
        if template_uses_pool(fn):
            for pool in (POOL, no_options):
                # Windows and branches are drawn per seed; the union over seeds
                # is the template's full operator set.
                for seed in range(12):
                    expr = fn(pool, random.Random(seed))
                    if expr:
                        actual |= called_identifiers(expr)
        else:
            actual = called_identifiers(fn("UNIQUE_FIELD_A", "UNIQUE_FIELD_B"))
        assert actual == set(declared), (
            f"{fn.__name__}: tag {sorted(declared)} != emitted {sorted(actual)} "
            f"(undeclared={sorted(actual - set(declared))}, never-emitted={sorted(set(declared) - actual)})"
        )
