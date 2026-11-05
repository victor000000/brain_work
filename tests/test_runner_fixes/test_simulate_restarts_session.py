"""FIX 15: auth failures never kill the process."""

import simulate_alphas as sa


def test_new_session_asks_for_raising_auth(monkeypatch):
    seen = {}

    def fake_get_session(raise_on_failure=False):
        seen["raise_on_failure"] = raise_on_failure
        raise SystemExit(2)  # legacy get_session exits on auth failure

    monkeypatch.setattr(sa, "get_session", fake_get_session)

    assert sa._session_or_none() is None
    assert seen == {"raise_on_failure": True}


def test_new_session_falls_back_for_legacy_signature(monkeypatch):
    monkeypatch.setattr(sa, "get_session", lambda: "session")
    assert sa._new_session() == "session"
