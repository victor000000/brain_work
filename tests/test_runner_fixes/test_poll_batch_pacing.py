"""FIX 3: poll_batch honors Retry-After on 200 and 429 without parking the
batch on a stale throttle flag."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import MagicMock

from runner import poll_batch as pb
from tests.test_runner_fixes.helpers import FakeResponse, batch_info
from tests.test_runner_fixes.test_poll_batch_errors_helpers import session_for, stored_parent  # noqa: F401


def test_retry_after_on_200_means_still_running(conn):
    info = batch_info()
    resp = FakeResponse(200, json_data={"progress": 0.4}, headers={"Retry-After": "5"})
    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is False
    assert info["retry_after"] == 5.0
    assert conn.execute("SELECT status, error_message FROM simulations WHERE sim_id='P1'").fetchone() == (
        "SUBMITTED",
        None,
    )


def test_http_date_retry_after_does_not_raise(conn):
    info = batch_info()
    when = datetime.now(UTC) + timedelta(seconds=60)
    resp = FakeResponse(200, json_data={"progress": 0.5}, headers={"Retry-After": format_datetime(when)})
    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is False
    assert 55 <= info["retry_after"] <= 61
    # Still pausable, and never a crash: the batch remains in flight.
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"


def test_429_sets_pacing_signals(conn):
    info = batch_info()
    resp = FakeResponse(429, headers={"Retry-After": "7"})
    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is False
    assert info["poll_throttled"] is True
    assert info["retry_after"] == 7.0


def test_leaving_the_computing_phase_records_an_advance(conn):
    """`last_advance_at` is the stale-drop's only liveness signal.

    It used to be written on the Retry-After path alone, so a batch whose parent
    had finished kept a last-advance timestamp from minutes earlier while its
    children were fetched, and `drop_stale` aborted it on age alone: B682 was
    dropped as "last progress 1169s ago" 64s after a poll had 9/10 of its
    children in hand. The fetch phase holds no BRAIN slot — the platform
    refuses the DELETE precisely because the sim is complete — so a drop there
    frees nothing.
    """
    info = batch_info()
    info["retry_after"] = 30.0
    info["poll_throttled"] = True
    assert "last_advance_at" not in info

    resp = FakeResponse(200, json_data={"status": "COMPLETE"})
    assert pb.poll_batch(session_for(resp), info, conn) is False

    assert "last_advance_at" in info, "a finished parent left the stale clock frozen"
    # Left the computing phase, so the pacing signals cannot keep a stale batch
    # parked in the next round either.
    assert "retry_after" not in info
    assert "poll_throttled" not in info


def test_children_arriving_are_progress(monkeypatch, conn):
    """A partial child fetch is motion, even though the parent stopped moving.

    One `handle_children` pass can outlast STALL_GRACE_SEC by itself — a child
    needing all three FETCH_RETRIES costs ~66s — and B680 was dropped with
    "last progress 1184s ago" while the poll before it had 7/10 children in
    hand. An empty pass must still not count as progress, or a genuinely
    frozen batch could never be dropped.
    """
    info = batch_info()
    monkeypatch.setattr(pb, "handle_children", lambda *a, **k: (3, 0, False))
    assert pb._poll_multi(None, info, ["C1", "C2", "C3"], conn, info["settings"], "now", 900) is False
    assert "last_advance_at" in info

    quiet = batch_info()
    monkeypatch.setattr(pb, "handle_children", lambda *a, **k: (0, 1, False))
    assert pb._poll_multi(None, quiet, ["C1"], conn, quiet["settings"], "now", 900) is False
    assert "last_advance_at" not in quiet


def test_non_429_error_clears_a_previous_throttle(conn):
    """A 429 then a 404 must not leave poll_throttled set forever.

    The stale-drop path defers whenever state["poll_throttled"] is true, so a
    sticky flag parks every stale batch until the end of the run.
    """
    info = batch_info()
    session = MagicMock()
    session.get.side_effect = [FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(404)]

    assert pb.poll_batch(session, info, conn) is False
    assert info["poll_throttled"] is True

    assert pb.poll_batch(session, info, conn) is False
    assert "poll_throttled" not in info
    assert "retry_after" not in info
