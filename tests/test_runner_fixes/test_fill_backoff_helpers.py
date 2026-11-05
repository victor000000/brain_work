"""Loop state and generator stub shared by the fill_slots backoff tests."""

from runner.explore_loop import fill


def make_state(**over):
    state = {
        "inflight": [],
        "batch_idx": 0,
        "submit_fail_streak": 0,
        "concurrent_streak": 0,
        "budget_exhausted": False,
    }
    state.update(over)
    return state


def install_generator(monkeypatch, results):
    """Stub generate_and_submit to replay `results`, then CONCURRENT forever."""
    calls = []

    def gen(session, conn, batch_idx):
        calls.append(batch_idx)
        if not results:
            return "CONCURRENT"
        return results.pop(0)

    monkeypatch.setattr(fill, "generate_and_submit", gen)
    monkeypatch.setattr(fill.time, "sleep", lambda *_: None)
    return calls
