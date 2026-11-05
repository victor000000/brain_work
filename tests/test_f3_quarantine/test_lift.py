"""Lift criteria: time-window expiry + hit-weight recovery override."""

import time

from tests.test_f3_quarantine.conftest import mem_conn, seed_alpha, seed_outcome


def test_quarantine_lifts_after_M_seconds():
    """A cell quarantined > M seconds ago is lifted on the next refresh."""
    import generator.priors_loader as pl

    conn = mem_conn()
    seed_alpha(conn, "a1", "old_quarantine")
    seed_outcome(conn, "old_quarantine", "MARKET", rejected=5)
    conn.commit()

    # First refresh: quarantines.
    pl.refresh_priors(conn)

    # Backdate quarantined_at to M+1 seconds ago.
    backdate = int(time.time()) - pl._QUARANTINE_DURATION_SECONDS - 1
    conn.execute(
        "UPDATE cell_priors SET quarantined_at = ? WHERE template = 'old_quarantine'",
        (backdate,),
    )
    conn.commit()

    # Second refresh: lift criteria check fires.
    pl.refresh_priors(conn)

    # Note: cell still has 5 rejections, so re-quarantines on the same refresh.
    # End state: quarantined=1 again, but with a fresh quarantined_at.
    new_qa = conn.execute("SELECT quarantined_at FROM cell_priors WHERE template='old_quarantine'").fetchone()[0]
    assert new_qa > backdate  # old timestamp was replaced


def test_quarantine_lifts_when_hit_weight_recovers():
    """A cell whose hit_weight crosses the recovery threshold is lifted even within M."""
    import generator.priors_loader as pl

    conn = mem_conn()
    # Seed many hits → high hit_weight will exceed the recovery threshold.
    for i in range(50):
        seed_alpha(conn, f"hit_{i}", "recovering_template", is_sharpe=2.0)
    seed_outcome(conn, "recovering_template", "MARKET", rejected=5)
    conn.commit()

    pl.refresh_priors(conn)

    # 50 hits / 50 count → hit_weight = 51 / (50+50) = 0.51 (well above 0.04 threshold).
    # Even though rejections >= K, the recovery branch wins.
    row = conn.execute("SELECT quarantined FROM cell_priors WHERE template='recovering_template'").fetchone()
    assert row[0] == 0
