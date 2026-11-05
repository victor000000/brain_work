"""Fake sessions shared by the auto re-auth hook tests."""

import threading


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class ScriptedSession:
    """Session whose request() replays a script of responses/exceptions."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url))
        item = self.script.pop(0) if self.script else FakeResponse(401)
        if isinstance(item, Exception):
            raise item
        return item


class BlockingAuthSession:
    """Every GET 401s; the auth POST blocks until the test releases it."""

    def __init__(self):
        self.auth_posts = 0
        self.auth_started = threading.Event()
        self.release_auth = threading.Event()
        self._lock = threading.Lock()

    def request(self, method, url, **kwargs):
        if method == "POST" and url.endswith("/authentication"):
            with self._lock:
                self.auth_posts += 1
            self.auth_started.set()
            assert self.release_auth.wait(timeout=5)
            return FakeResponse(200)
        return FakeResponse(401)
