"""The check thread must not reuse the loop's HTTP session.

`requests.Session` is not thread-safe, and the check thread runs for up to
1200s while the main loop keeps using whatever session it was handed. Sharing
one corrupted the connection pool: inside a check run, 44 of 66 previews came
back HTTP 200 with an empty body and burned the full 45s deadline, while the
same requests from a single-threaded caller returned bodies in under two
seconds, 0 of 10 empty.
"""

from runner.explore_helpers import background_check as bc


def test_the_check_thread_opens_its_own_session(monkeypatch):
    sessions, ran = [], []
    monkeypatch.setattr(bc, "get_session", lambda: sessions.append(object()) or "own-session")
    monkeypatch.setattr(bc, "get_conn", lambda: type("C", (), {"close": lambda self: None})())
    monkeypatch.setattr(bc, "check_new_alphas", lambda s, c: ran.append(s))

    bc._run_check_in_thread()

    assert sessions, "the check thread did not open its own session"
    assert ran == ["own-session"], "the check ran against a session it does not own"


def test_start_background_check_takes_no_session():
    """The loop's session must not be a parameter, or it will be passed again."""
    import inspect

    assert list(inspect.signature(bc.start_background_check).parameters) == []
