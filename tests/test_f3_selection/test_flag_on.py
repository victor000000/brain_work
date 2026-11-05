"""BRAIN_FEEDBACK_LOOP=1 — high-yield cells dominate, unknowns use prior."""

import random

from tests.test_f3_selection.conftest import make_template, mem_conn, seed_priors


def test_weighted_choice_flag_on_biases_to_high_yield(monkeypatch):
    """With BRAIN_FEEDBACK_LOOP=1, the high-hit_weight template dominates picks."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "1")
    from generator import cell_priors
    from generator import weighted_selection as ws

    conn = mem_conn()
    seed_priors(
        conn,
        [
            ("hi_yield", "USA", "TOP3000", 1, 0.20, 0),  # 20x the low-yield
            ("lo_yield", "USA", "TOP3000", 1, 0.01, 0),
        ],
    )
    cell_priors.load_priors(conn)
    ws.load_usage(conn)

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
    # Before ε-floor: ratio is 20:1 → ~95.2%/4.8% split. Allow 90%-99% range.
    assert counts["hi_yield"] > 1800
    assert counts["lo_yield"] > 0  # nonzero (sanity)


def test_weighted_choice_unknown_cell_uses_prior(monkeypatch):
    """An unknown (template, region, universe, delay) cell uses prior mean (0.02)."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "1")
    from generator import cell_priors
    from generator import weighted_selection as ws

    conn = mem_conn()
    # Seed only ONE of the two templates; the other is unknown.
    seed_priors(conn, [("known", "USA", "TOP3000", 1, 0.10, 0)])
    cell_priors.load_priors(conn)
    ws.load_usage(conn)

    t_known = make_template("known")
    t_unknown = make_template("unknown")
    counts = {"known": 0, "unknown": 0}

    # 0.10 vs prior 0.02 = 5:1 ratio.
    random.seed(0)
    for _ in range(2000):
        _, name = ws.weighted_choice(
            [(t_known, ["op_a"]), (t_unknown, ["op_a"])],
            cell_context=("USA", "TOP3000", 1, "MARKET"),
        )
        counts[name] += 1
    # 5:1 ratio → ~83.3%/16.7%.
    assert counts["known"] > 1500
    assert counts["unknown"] > 100
