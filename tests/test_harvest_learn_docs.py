"""Filename logic for the learn-documentation harvest.

Page ids are slugs from the BRAIN API. They must survive a round trip to a
filesystem name so a re-run can recognise a page it already holds — the resume
path matches on the suffix, so a lost or mangled slug means re-fetching.
"""

import json
import os

import pytest

from tools.harvest_learn_docs import safe_name, write_json


def test_plain_slug_is_unchanged():
    assert safe_name("superalpha-overview") == "superalpha-overview"


def test_path_separators_are_replaced():
    assert "/" not in safe_name("a/b")
    assert safe_name("a/b") == "a-b"


def test_unsafe_characters_are_replaced():
    assert safe_name("what is this?") == "what-is-this"
    assert safe_name("a:b*c") == "a-b-c"


def test_dots_and_underscores_survive():
    """Both appear in real page ids and must not be rewritten."""
    assert safe_name("getting-started.on_gbr") == "getting-started.on_gbr"


def test_empty_or_symbol_only_falls_back():
    assert safe_name("") == "page"
    assert safe_name("///") == "page"


def test_leading_and_trailing_separators_are_stripped():
    assert safe_name("-abc-") == "abc"
    assert safe_name("__x__") == "__x__"  # underscores are legal, kept as-is


# ── atomic cache writes ───────────────────────────────────────────
#
# A truncated page JSON used to be left behind by an interrupted write, and the
# next run raised on json.load of that cache entry.


def test_write_json_round_trips(tmp_path):
    path = tmp_path / "page.json"
    write_json(path, {"title": "x", "content": [1, 2]})
    assert json.loads(path.read_text()) == {"title": "x", "content": [1, 2]}


def test_write_json_replaces_existing_content(tmp_path):
    path = tmp_path / "page.json"
    path.write_text('{"old": true}')
    write_json(path, {"new": True})
    assert json.loads(path.read_text()) == {"new": True}


def test_write_json_leaves_no_temp_files(tmp_path):
    write_json(tmp_path / "page.json", {"a": 1})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page.json"]


def test_write_json_failure_leaves_the_original_intact(tmp_path, monkeypatch):
    path = tmp_path / "page.json"
    path.write_text('{"old": true}')

    def boom(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_json(path, {"new": True})

    assert json.loads(path.read_text()) == {"old": True}
    # the temp file must not be left behind either
    assert [p.name for p in tmp_path.iterdir()] == ["page.json"]
