"""FIX 2: the re-attach cap is a batch count, not the submission budget, and
hitting it must never be silent."""

import time

from runner.explore_loop import reattach as reattach_mod
from runner.explore_loop.reattach import (
    REATTACH_MAX_BATCHES,
    reattach_orphans,
)
from tests.test_runner_fixes.test_reattach_helpers import parent, ts


def test_reattach_default_cap_is_not_the_submission_budget(conn):
    """Tying the re-attach cap to `max_concurrent` stranded simulations.

    A restart re-attached exactly `max_concurrent` orphans, so the ones past
    the cap kept running on BRAIN with nothing polling them — and the loop,
    seeing a short `inflight` list, immediately submitted more, overrunning the
    account's concurrent-simulation limit. Observed 2026-10-06: three restarts
    in six minutes returned exactly the cap, and whole batches came back
    CANCELLED within seconds of submission.
    """
    now = time.time()
    for i in range(12):
        parent(conn, f"P{i}", i, ts(now - i))

    batches = reattach_orphans(conn, now=now)

    assert len(batches) == 12, "orphans past the old cap were stranded"
    assert REATTACH_MAX_BATCHES > 8  # no longer pinned to max_concurrent


def test_reattach_warns_when_it_hits_the_cap(conn, monkeypatch):
    """A stranded orphan must never be silent."""
    now = time.time()
    for i in range(3):
        parent(conn, f"P{i}", i, ts(now - i))
    seen = []
    monkeypatch.setattr(reattach_mod.elog, "warning", lambda *a, **k: seen.append(a[0] % a[1:]))

    reattach_orphans(conn, limit=3, now=now)

    assert any("cap of 3" in m for m in seen), seen
