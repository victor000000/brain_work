"""Auto re-auth hook: failure recovery.

The session is shared with background threads, so a failed auth POST must not
leave `_reauthing` stuck True (which silently disables re-auth forever).
"""

import core.reauth as reauth
from tests.test_reauth_helpers import FakeResponse, ScriptedSession


def test_exception_in_auth_does_not_lock_out_reauth():
    session = ScriptedSession(
        [
            FakeResponse(401),  # initial request
            ConnectionError("connection reset"),  # auth POST raises
            FakeResponse(401),  # next request → 401 again
            FakeResponse(200),  # auth POST succeeds
            FakeResponse(200),  # retried request
        ]
    )
    reauth._install_reauth_hook(session, "https://api.example", reauth_cooldown=0)

    first = session.request("GET", "https://api.example/alphas")
    assert first.status_code == 401
    assert session._reauthing is False

    # A failed attempt must not poison the session: the next 401 re-auths.
    second = session.request("GET", "https://api.example/alphas")
    assert second.status_code == 200
    posts = [c for c in session.calls if c[0] == "POST"]
    assert len(posts) == 2, session.calls


def test_failed_auth_response_clears_reauthing_and_allows_retry():
    session = ScriptedSession(
        [
            FakeResponse(401),
            FakeResponse(401, text="bad credentials"),  # auth POST rejected
            FakeResponse(401),
            FakeResponse(201),  # auth POST accepted on retry
            FakeResponse(201),  # retried request
        ]
    )
    reauth._install_reauth_hook(session, "https://api.example", reauth_cooldown=0)

    assert session.request("GET", "/x").status_code == 401
    assert session._reauthing is False
    assert session.request("GET", "/x").status_code == 201
    posts = [c for c in session.calls if c[0] == "POST"]
    assert len(posts) == 2
