"""Thought mining: the prose block around a template's example."""

from tools.mine_template_thoughts import _rank, collect, paragraph_around


def test_paragraph_around_returns_the_block_containing_the_line():
    text = "Intro line\n\nHypothesis: the signal pays in EUR.\nts_rank(close,20) with INDUSTRY neutralization.\n\nNext topic"
    block = paragraph_around(text, "ts_rank(close,20) with INDUSTRY neutralization.")
    assert block is not None and "Hypothesis" in block and "Next topic" not in block


def test_paragraph_around_falls_back_to_a_neighbourhood_window():
    """A bare code line has no blank-line block; neighbours are the context."""
    text = "\n".join(
        [f"comment {i}" for i in range(6)] + ["ts_delta(close,5)"] + [f"comment {i}" for i in range(6, 12)]
    )
    block = paragraph_around(text, "ts_delta(close,5)")
    assert block is not None
    assert "comment 5" in block and "comment 7" in block


def test_paragraph_around_returns_none_when_the_line_is_absent():
    assert paragraph_around("nothing here", "ts_delta(close,5)") is None


def test_paragraph_around_uses_the_window_in_a_long_blank_line_free_document():
    """Every line of a blank-line-free dump used to get the same document head."""
    lines = [f"chatty line {i} about nothing in particular" for i in range(30)]
    lines[20] = "ts_delta(close,5) is the signal"
    block = paragraph_around("\n".join(lines), "ts_delta(close,5) is the signal")
    assert block is not None
    assert "ts_delta(close,5) is the signal" in block
    assert "chatty line 19" in block


def test_paragraph_around_keeps_the_line_with_long_neighbours():
    """The window is cut at MAX_THOUGHT_CHARS; the line must survive the cut."""
    lines = [f"chatty line {i} " + "x" * 90 for i in range(30)]
    lines[20] = "ts_delta(close,5) is the signal"
    block = paragraph_around("\n".join(lines), "ts_delta(close,5) is the signal")
    assert block is not None
    assert "ts_delta(close,5) is the signal" in block


def test_collect_joins_thoughts_to_the_same_skeleton_the_miner_builds():
    docs = [
        (
            "post",
            "1",
            "Why this works: volume spike predicts reversal.\n\nrank(ts_delta(close,5))\n\nwith 21-day decay.",
        )
    ]
    posts = {"1": {"title": "Volume reversal", "html_url": "https://forum/x", "created_at": "2026-01-01"}}
    thoughts = collect(docs, posts)
    assert "rank(ts_delta({f},5))" in thoughts
    thought = thoughts["rank(ts_delta({f},5))"][0]
    assert thought["title"] == "Volume reversal"
    assert "volume spike" in thought["text"]
    assert thought["url"] == "https://forum/x"


def test_telling_prose_outranks_a_bare_restatement():
    decision = {"text": "Sharpe 1.9 after INDUSTRY neutralization, turnover 0.12.", "source": "comment"}
    bare = {"text": "ts_rank(close,20)", "source": "comment"}
    assert _rank(decision) > _rank(bare)


def test_code_paragraphs_are_demoted():
    prose = {"text": "This template standardizes within sector.", "source": "post"}
    code = {"text": "def build(self):\n    return rank(x)", "source": "post"}
    assert _rank(prose) > _rank(code)
