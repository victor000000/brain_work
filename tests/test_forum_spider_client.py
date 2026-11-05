"""ForumClient failure semantics: a failed fetch is not cached as empty."""


def test_post_body_returns_none_on_failed_fetch():
    """A failed fetch must not be indistinguishable from an empty body."""
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    client.get_json = lambda *a, **k: None
    assert client.post_body(123) is None


def test_post_body_returns_empty_string_only_on_a_real_empty_body():
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    client.get_json = lambda *a, **k: {"post": {"id": 1, "details": ""}}
    assert client.post_body(1) == ""

    client.get_json = lambda *a, **k: {"post": {"id": 1}}
    assert client.post_body(1) == ""


def test_post_body_malformed_response_is_a_failure():
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    client.get_json = lambda *a, **k: {}
    assert client.post_body(1) is None


def test_comments_returns_none_when_page_one_fails():
    """The old code cached [] on a page-1 failure, permanently."""
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    client.get_json = lambda *a, **k: None
    assert client.comments(5) is None


def test_comments_returns_none_on_a_mid_pagination_failure():
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    responses = [
        {"comments": [{"id": 1}], "page_count": 2},
        None,
    ]
    client.get_json = lambda *a, **k: responses.pop(0)
    assert client.comments(5) is None


def test_comments_genuinely_empty_post_returns_empty_list():
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    client.get_json = lambda *a, **k: {"comments": [], "page_count": 1}
    assert client.comments(5) == []


def test_comments_paginates_to_the_end():
    from download.forum.client import ForumClient

    client = ForumClient.__new__(ForumClient)
    responses = [
        {"comments": [{"id": 1}], "page_count": 2},
        {"comments": [{"id": 2}], "page_count": 2},
    ]
    client.get_json = lambda *a, **k: responses.pop(0)
    assert client.comments(5) == [{"id": 1}, {"id": 2}]


def test_authenticate_retries_the_transport_failures_that_killed_two_crawls(monkeypatch):
    """Measured 2026-10-15: SSLEOFError at the zendesk JWT hop and the
    platform sign-in hop aborted whole crawl runs, because `get_json`'s
    content retries cannot survive an auth raise from inside their handler."""
    import download.forum.client_auth as mod
    from download.forum.client_auth import _AuthMixin

    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    calls = []

    def once():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("EOF occurred in violation of protocol")

    mixin = _AuthMixin.__new__(_AuthMixin)
    mixin._authenticate_once = once
    mixin.authenticate()
    assert len(calls) == 3, "two transport failures, third attempt succeeds"


def test_authenticate_reraises_after_the_attempts(monkeypatch):
    import download.forum.client_auth as mod
    from download.forum.client_auth import _AuthMixin

    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    calls = []

    def once():
        calls.append(1)
        raise ConnectionError("EOF occurred in violation of protocol")

    mixin = _AuthMixin.__new__(_AuthMixin)
    mixin._authenticate_once = once
    try:
        mixin.authenticate()
        raise AssertionError("should have re-raised")
    except ConnectionError:
        pass
    assert len(calls) == 3
