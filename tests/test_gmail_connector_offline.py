"""Connector lifecycle and request shape without launching Codex or Gmail."""

from types import SimpleNamespace

from tools.brain_gmail_connector import CodexGmail


def test_reader_can_finish_when_process_is_already_closed():
    client = CodexGmail()
    client._read_loop()
    client.proc = SimpleNamespace(stdout=None)
    client._read_loop()
    assert client._replies.empty()


def test_reader_retains_stream_when_close_clears_the_process_reference():
    client = CodexGmail()

    def stream():
        client.proc = None
        yield '{"id": 7, "result": {}}\n'

    client.proc = SimpleNamespace(stdout=stream())
    client._read_loop()
    assert client._replies.get_nowait() == {"id": 7, "result": {}}


def test_search_omits_absent_cursor_and_preserves_an_explicit_cursor(monkeypatch):
    client = CodexGmail()
    calls = []

    def call(tool, args):
        calls.append((tool, args))
        return {"structuredContent": {"emails": []}}

    monkeypatch.setattr(client, "call", call)
    assert client.search("research") == {"emails": []}
    client.search_ids("research", next_page_token="page-two")
    assert calls == [
        ("gmail.search_emails", {"query": "research", "max_results": 100}),
        ("gmail.search_email_ids", {"query": "research", "max_results": 500, "next_page_token": "page-two"}),
    ]
