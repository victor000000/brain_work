"""Pure logic for the forum spider — checkpointing, resume, HTML stripping."""

import json

from download.forum.spider import (
    html_to_text,
    load_checkpoint,
    pending_ids,
    save_checkpoint,
)


def test_html_to_text_strips_tags_and_keeps_breaks():
    html = "<p>first line<br/>second</p><p>third</p>"
    text = html_to_text(html)
    assert "first line" in text
    assert "second" in text
    assert "third" in text
    assert "<" not in text
    assert text.count("\n") >= 2


def test_html_to_text_unescapes_entities():
    assert "a < b & c > d" in html_to_text("a &lt; b &amp; c &gt; d")


def test_html_to_text_handles_empty():
    assert html_to_text("") == ""
    assert html_to_text(None) == ""


def test_pending_ids_excludes_already_fetched():
    assert pending_ids([1, 2, 3, 4], {"2": "x", "4": "y"}) == [1, 3]


def test_pending_ids_all_pending_when_checkpoint_empty():
    assert pending_ids([1, 2], {}) == [1, 2]


def test_checkpoint_roundtrip(tmp_path):
    path = tmp_path / "cp.json"
    save_checkpoint(path, {"1": "body one"})
    assert load_checkpoint(path) == {"1": "body one"}


def test_checkpoint_missing_file_is_empty(tmp_path):
    assert load_checkpoint(tmp_path / "nope.json") == {}


def test_checkpoint_survives_corrupt_file(tmp_path):
    """A truncated checkpoint must not lose the run — treat it as empty."""
    path = tmp_path / "cp.json"
    path.write_text('{"1": "body", "2":')
    assert load_checkpoint(path) == {}


def test_save_checkpoint_is_valid_json(tmp_path):
    path = tmp_path / "cp.json"
    save_checkpoint(path, {"a": "b"})
    assert json.loads(path.read_text()) == {"a": "b"}
