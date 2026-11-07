"""Offline Markdown checks must catch broken references without following the network."""

import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/check_docs.py"
spec = importlib.util.spec_from_file_location("owned_docs_checker", MODULE)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_local_targets_and_duplicate_unicode_anchors(tmp_path):
    (tmp_path / "README.md").write_text("[guide](guide.md#hello-1) [中文](guide.md#中文)")
    (tmp_path / "guide.md").write_text("# Hello\n# Hello\n# 中文\n")
    count, errors = checker.check(tmp_path)
    assert count == 2
    assert errors == []


def test_missing_link_anchor_and_escape_are_rejected(tmp_path):
    (tmp_path / "README.md").write_text("[a](missing.md) [b](#missing) [c](../outside.md)")
    _, errors = checker.check(tmp_path)
    assert len(errors) == 3
    assert any("missing target" in e for e in errors)
    assert any("missing heading anchor" in e for e in errors)
    assert any("escapes repository" in e for e in errors)


def test_code_fences_external_links_and_vendor_content_are_excluded(tmp_path):
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor/upstream.md").write_text("[upstream](missing.md)")
    (tmp_path / "README.md").write_text("```md\n[example](missing.md)\n```\n[external](https://example.invalid/)")
    count, errors = checker.check(tmp_path)
    assert count == 1
    assert errors == []


def test_encoded_filename_is_resolved(tmp_path):
    (tmp_path / "README.md").write_text("[guide](my%20guide.md#heading)")
    (tmp_path / "my guide.md").write_text("# Heading\n")
    assert checker.check(tmp_path)[1] == []


def test_virtualenv_and_generated_cache_docs_are_excluded(tmp_path):
    (tmp_path / ".venv310").mkdir()
    (tmp_path / ".venv310/README.md").write_text("[package](missing.md)")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache/README.md").write_text("[cache](missing.md)")
    assert checker.check(tmp_path) == (0, [])
