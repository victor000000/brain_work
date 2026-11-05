"""Biased template picker — coverage * cell_priors * shape_prior weighting."""

import os
import random

from generator.weighted_selection.state import get_weight

# ε-floor: a quarantined cell still receives 5% of its baseline coverage
# weight, keeping exploration alive (without this, a quarantined cell with
# hw == 0 gets 0 weight and would never be sampled, blocking recovery).
EPS_FRACTION = 0.05


def _feedback_loop_enabled():
    """Feedback loop is on by default. Set BRAIN_FEEDBACK_LOOP=0 to opt out."""
    return os.environ.get("BRAIN_FEEDBACK_LOOP", "1") != "0"


def _cell_biased_weights(templates_with_ops, coverage_weights, cell_context):
    """Multiply coverage weights by cell hit_weight * expected_multiplier * shape * oos."""
    # Local imports to avoid load-order cycles between generator submodules.
    from generator import cell_priors, corr_prior, shape_prior

    region, universe, delay, _neutralization = cell_context
    weights = []
    for (fn, _ops), cov_w in zip(templates_with_ops, coverage_weights, strict=True):
        name = fn.__name__
        hw = cell_priors.hit_weight(name, region, universe, delay)
        mult = cell_priors.expected_multiplier(name, region, universe, delay)
        shape = shape_prior.shape_weight(name)
        oos = cell_priors.oos_robustness(name, region, universe, delay)
        # hit_weight says "reaches the sharpe floor"; corr_weight says "and is
        # not correlated once it does" — the product is what a submission
        # needs, and correlation is the gate that actually binds.
        corr = corr_prior.corr_weight(name, cell=(region, universe, delay))
        # Only clamp up to EPS_FRACTION when hw is exactly 0 (quarantined);
        # legitimate low-hit cells keep their true posterior weight.
        effective_hw = EPS_FRACTION if hw == 0.0 else hw
        weights.append(cov_w * effective_hw * mult * shape * oos * corr)
    return weights


def weighted_choice(templates_with_ops, *, cell_context=None):
    """Pick a template weighted by inverse operator usage.

    When cell_context is given AND the feedback loop is enabled (default;
    BRAIN_FEEDBACK_LOOP=0 to opt out), additionally biases by cell-level
    hit_weight * expected_multiplier * shape_weight * oos_robustness.

    Returns (template_fn, template_name).
    """
    coverage_weights = [get_weight(ops) for _fn, ops in templates_with_ops]

    if cell_context is None or not _feedback_loop_enabled():
        weights = coverage_weights
    else:
        weights = _cell_biased_weights(templates_with_ops, coverage_weights, cell_context)

    total = sum(weights)
    if total <= 0:
        # Pathological: all weights zero. Fall back to uniform random.
        fn = random.choice(templates_with_ops)[0]
        return fn, fn.__name__
    rand_val = random.random() * total
    cumulative = 0.0
    for i, (fn, _ops) in enumerate(templates_with_ops):
        cumulative += weights[i]
        if rand_val <= cumulative:
            return fn, fn.__name__
    fn = templates_with_ops[-1][0]
    return fn, fn.__name__
