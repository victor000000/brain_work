"""weighted_choice multiplies cov_w * effective_hw * mult * shape * oos."""

from unittest.mock import patch

import pytest

from generator import cell_priors, shape_prior


def fake_template_a():
    return None


def fake_template_b():
    return None


def test_oos_robustness_factor_applied():
    """A cell with high oos_robustness should outweight one with low oos."""
    templates_with_ops = [
        (fake_template_a, []),
        (fake_template_b, []),
    ]

    def fake_oos(name, region, universe, delay):
        return 0.9 if name == "fake_template_a" else 0.1

    with (
        patch.object(cell_priors, "oos_robustness", side_effect=fake_oos),
        patch.object(cell_priors, "hit_weight", return_value=0.05),
        patch.object(cell_priors, "expected_multiplier", return_value=1.0),
        patch.object(shape_prior, "shape_weight", return_value=1.0),
    ):
        from generator.weighted_selection.choice import _cell_biased_weights

        weights = _cell_biased_weights(
            templates_with_ops,
            coverage_weights=[1.0, 1.0],
            cell_context=("CHN", "TOP2000U", 0, "NONE"),
        )
    assert weights[0] / weights[1] == pytest.approx(9.0)


def test_unknown_cell_uses_default_oos():
    """Unknown cells get the 0.5 default."""
    from generator.cell_priors import oos_robustness

    assert oos_robustness("never_seen", "X", "Y", 0) == 0.5
