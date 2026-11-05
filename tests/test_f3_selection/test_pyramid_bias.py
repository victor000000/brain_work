"""expected_multiplier shifts selection probability proportionally."""

import random
import time

from tests.test_f3_selection.conftest import make_template, mem_conn


def test_weighted_choice_pyramid_bias_under_flag(monkeypatch):
    """A cell with high expected_multiplier outweighs equal-hit-weight peers."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "1")
    from generator import cell_priors
    from generator import weighted_selection as ws

    conn = mem_conn()
    now = int(time.time())
    # Two cells, identical hit_weight (0.10), different expected_multiplier
    # (1.9 vs 1.0 -> 1.9x selection ratio).
    for tmpl, em in [("hi_mult", 1.9), ("lo_mult", 1.0)]:
        conn.execute(
            "INSERT INTO cell_priors "
            "(template, region, universe, delay, count, hits, hit_weight, "
            " expected_multiplier, quarantined, quarantined_at, refreshed_at) "
            "VALUES (?, 'USA', 'TOP3000', 1, 100, 10, 0.10, ?, 0, NULL, ?)",
            (tmpl, em, now),
        )
    conn.commit()
    cell_priors.load_priors(conn)
    ws.load_usage(conn)

    t_hi = make_template("hi_mult")
    t_lo = make_template("lo_mult")
    counts = {"hi_mult": 0, "lo_mult": 0}

    random.seed(0)
    for _ in range(2000):
        _, name = ws.weighted_choice(
            [(t_hi, ["op_a"]), (t_lo, ["op_a"])],
            cell_context=("USA", "TOP3000", 1, "MARKET"),
        )
        counts[name] += 1
    # 1.9:1 ratio → ~65.5% / 34.5% split. Generous Monte Carlo tolerance.
    assert counts["hi_mult"] > 1200
    assert counts["lo_mult"] > 500
