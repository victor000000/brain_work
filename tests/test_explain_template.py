"""The reader for `docs/forum/template_thoughts.json`."""

from tools.explain_template import excerpt, format_row, match_rows

TAIL = "tail(group_zscore({f}, sector), lower=-{n}, upper={n}, newval=0)"
MOM = "rank(ts_delta({f}, {n}))"

CORPUS = {
    TAIL: {
        "thoughts": [
            {
                "source": "post",
                "title": "PC 相关性管理",
                "created_at": "2026-10-01T00:00:00Z",
                "url": "https://example.invalid/1",
                "text": "使用 tail(group_zscore(x,industry), lower=-1.1, upper=1.1, newval=0) " * 4,
            }
        ]
    },
    MOM: {"thoughts": [{"source": "comment", "text": "cross-sectional momentum variant"}]},
}


def test_match_by_skeleton_substring():
    assert [s for s, _ in match_rows(CORPUS, "tail(")] == [TAIL]


def test_match_by_thought_text():
    rows = match_rows(CORPUS, "momentum")
    assert len(rows) == 1
    assert rows[0][0] == MOM


def test_match_is_case_insensitive_and_respects_the_limit():
    assert len(match_rows(CORPUS, "TAIL")) == 1
    assert len(match_rows(CORPUS, "", limit=1)) == 1


def test_format_row_trims_the_excerpt_and_keeps_the_provenance():
    skeleton, thoughts = match_rows(CORPUS, "tail(")[0]
    out = format_row(skeleton, thoughts, chars=60, per_row=1)
    assert out.startswith(f"=== {TAIL}")
    assert "…" in out, "long text should be trimmed"
    assert "2026-10-01" in out, "the post date should survive"
    assert "https://example.invalid/1" in out


def test_excerpt_collapses_whitespace():
    assert excerpt("a\n\n  b\t c", 100) == "a b c"
    assert excerpt("x" * 50, 10) == "x" * 10 + "…"
    assert excerpt(None, 10) == ""
