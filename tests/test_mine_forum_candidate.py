"""Forum text must parse before it can become a fillable template."""

import pytest

from tools.mine_forum_candidate import looks_like_alpha, normalize_expression_line
from tools.mine_forum_classify import classify, residual_tokens
from tools.mine_forum_scan import build_rows, scan_documents
from tools.mine_forum_text import iter_text, skeletonize
from tools.mine_thoughts_collect import collect


@pytest.mark.parametrize(
    "expression",
    [
        "trade_when(volume>adv20,rank(close),-1)",
        "if_else(close<=open,rank(close),rank(volume))",
        "if_else(close!=open,rank(close),rank(volume))",
        "winsorize(close,std=3)",
        'group_rank(close,bucket(rank(cap),range="0,1,0.1"))',
        "ts_target_tvr_decay(close,target_tvr=0.1)",
        "rank({f})",
    ],
)
def test_recognizes_complete_expression_syntax(expression):
    assert looks_like_alpha(expression)


@pytest.mark.parametrize(
    "prose",
    [
        "Step 4 Avoid rank(-assets) and 1-rank(cap)",
        '"""Approximate percentile rank(0-1) for each asset."""',
        "Ts_median(signal,2) also works perfectly in this case",
        "rank(<name/>)",
        "rank(close) trailing prose",
        "price=rank(close); other=rank(volume)",
    ],
)
def test_rejects_prose_and_incomplete_programs(prose):
    assert not looks_like_alpha(prose)


def test_named_argument_keys_are_positional_and_literals_survive():
    expression = 'group_rank(close,bucket(rank(cap),range="0, 1, 0.1"))'
    skeleton = skeletonize(expression)
    assert skeleton == 'group_rank({f},bucket(rank({f}),range="0, 1, 0.1"))'
    assert classify(expression, ({"close", "cap"}, set())) == ({"close", "cap"}, set())
    assert not residual_tokens(skeleton)
    # The same identifier can be an input field and a keyword in one call.
    expression = "ts_target_tvr_decay(target_tvr,target_tvr=0.1)"
    assert looks_like_alpha(expression)
    assert skeletonize(expression) == "ts_target_tvr_decay({f},target_tvr=0.1)"
    assert classify(expression, ({"target_tvr"}, set())) == ({"target_tvr"}, set())
    assert classify("winsorize(std,std=3)", ({"std"}, set())) == ({"std"}, set())
    assert skeletonize("winsorize(std,std=3)") == "winsorize({f},std=3)"


def test_assignment_normalization_preserves_complete_programs_and_quoted_comments():
    assert normalize_expression_line("price=rank(ts_sum(returns,126));") == "rank(ts_sum(returns,126))"
    assert normalize_expression_line("alpha: rank(close); # rationale") == "rank(close)"
    assert normalize_expression_line("x=rank(close);x") == "x=rank(close);x"
    assert normalize_expression_line('quantile(close,driver="a#b//c") # note') == 'quantile(close,driver="a#b//c")'


def test_miner_and_thoughts_join_normalized_assignment_with_original_provenance():
    bodies = {"1": "<p>Momentum hypothesis: persistent returns.</p><p>price=rank(ts_sum(returns,126));</p>"}
    posts = {"1": {"title": "Momentum", "html_url": "https://forum.example/1"}}
    mined = scan_documents(bodies, {}, ({"returns"}, {"pv1"}))
    rows = build_rows(*mined[:3], posts)
    assert len(rows) == 1
    assert rows[0]["skeleton"] == "rank(ts_sum({f},126))"
    assert rows[0]["fillable_from_pv_option"]
    thoughts = collect(iter_text(bodies, {}), posts)
    thought = thoughts[rows[0]["skeleton"]][0]
    assert "price=rank(ts_sum(returns,126));" in thought["text"]
    assert thought["url"] == posts["1"]["html_url"]
