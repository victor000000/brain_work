"""Auto re-auth hook: concurrent 401s must fire exactly one auth POST."""

import threading

import core.reauth as reauth
from tests.test_reauth_helpers import BlockingAuthSession


def test_concurrent_401s_fire_only_one_auth_post():
    session = BlockingAuthSession()
    reauth._install_reauth_hook(session, "https://api.example", reauth_cooldown=30)
    errors = []

    def worker():
        try:
            session.request("GET", "https://api.example/simulations")
        except Exception as err:  # pragma: no cover - failure path
            errors.append(err)

    first = threading.Thread(target=worker)
    first.start()
    assert session.auth_started.wait(timeout=5), "auth POST never started"

    # These threads all hit 401 and must queue behind the in-flight re-auth.
    others = [threading.Thread(target=worker) for _ in range(4)]
    for t in others:
        t.start()
    session.release_auth.set()

    for t in [first, *others]:
        t.join(timeout=5)
        assert not t.is_alive()

    assert not errors
    assert session.auth_posts == 1
    assert session._reauthing is False
