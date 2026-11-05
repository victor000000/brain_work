"""shape_prior 0.0 fully excludes a template under the feedback flag."""

import random

from tests.test_f3_selection.conftest import make_template, mem_conn


def test_weighted_choice_shape_prior_zero_excludes_template(monkeypatch):
    """A template with shape_weight 0.0 is fully excluded under the flag."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "1")
    from generator import cell_priors, shape_prior
    from generator import weighted_selection as ws

    conn = mem_conn()
    cell_priors.load_priors(conn)  # empty -> all cells get prior 0.02 + default mult 1.0
    ws.load_usage(conn)
    monkeypatch.setitem(shape_prior._SHAPE_WEIGHTS, "blocked", 0.0)
    monkeypatch.setitem(shape_prior._SHAPE_WEIGHTS, "allowed", 1.0)

    t_blocked = make_template("blocked")
    t_allowed = make_template("allowed")
    counts = {"blocked": 0, "allowed": 0}

    random.seed(0)
    for _ in range(1000):
        _, name = ws.weighted_choice(
            [(t_blocked, ["op_a"]), (t_allowed, ["op_a"])],
            cell_context=("USA", "TOP3000", 1, "MARKET"),
        )
        counts[name] += 1
    # blocked * shape 0.0 = 0; allowed * 1.0 = full; blocked never picked.
    assert counts["blocked"] == 0
    assert counts["allowed"] == 1000
