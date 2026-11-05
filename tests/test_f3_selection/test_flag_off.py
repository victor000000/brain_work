"""BRAIN_FEEDBACK_LOOP=0 — cell_context has no effect on weights."""

import random

from tests.test_f3_selection.conftest import make_template, mem_conn, seed_priors


def test_weighted_choice_flag_off_ignores_cell_context(monkeypatch):
    """With BRAIN_FEEDBACK_LOOP=0, cell_context has no effect (opt-out path)."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "0")
    from generator import cell_priors
    from generator import weighted_selection as ws

    conn = mem_conn()
    seed_priors(
        conn,
        [
            ("hi_yield", "USA", "TOP3000", 1, 0.20, 0),
            ("lo_yield", "USA", "TOP3000", 1, 0.01, 0),
        ],
    )
    cell_priors.load_priors(conn)
    ws.load_usage(conn)  # zero usage; coverage weights equal

    t_hi = make_template("hi_yield")
    t_lo = make_template("lo_yield")
    counts = {"hi_yield": 0, "lo_yield": 0}

    random.seed(0)
    for _ in range(2000):
        _, name = ws.weighted_choice(
            [(t_hi, ["op_a"]), (t_lo, ["op_a"])],
            cell_context=("USA", "TOP3000", 1, "MARKET"),
        )
        counts[name] += 1
    # 50/50 ± Monte Carlo noise (binomial 2000 trials, p=0.5, 3-sigma ~ ±70).
    assert 900 < counts["hi_yield"] < 1100
    assert 900 < counts["lo_yield"] < 1100
