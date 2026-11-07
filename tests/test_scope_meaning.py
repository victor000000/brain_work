import pytest

from core.scope import classify_leaf, dispatch_block_reason, validate_expression


def test_consensus_field_is_not_pv():
    # pv87 prefix, analyst meaning: must NOT be treated as price/volume.
    assert classify_leaf("pv87_ebt_normalized_consensus_high_scale") == "analyst"
    assert classify_leaf("pv87_revenue_consensus_median_scale") == "analyst"


def test_consensus_expression_is_a_violation():
    v = validate_expression("group_zscore(pv87_ebt_normalized_consensus_high_scale, sector)")
    assert v["status"] == "violation"
    assert "pv87_ebt_normalized_consensus_high_scale" in v["blocked"]


def test_estimate_suffix_is_analyst():
    assert classify_leaf("pv87_eps_estimate_scale") == "analyst"


def test_genuine_pv_leaf_still_permitted():
    v = validate_expression("rank(volume / ts_mean(volume, 20))")
    assert v["status"] == "ok"
    assert v["permitted"] == ["volume"]


def test_pv_spread_field_still_permitted():
    assert classify_leaf("pv106_spreadbp") == "pv"
    assert validate_expression("rank(pv106_spreadbp)")["status"] == "ok"


def test_option_leaf_still_permitted():
    assert validate_expression("rank(implied_volatility)")["status"] == "ok"


@pytest.mark.parametrize("prefix", ["pv87", "opt3"])
@pytest.mark.parametrize(
    ("suffix", "category"),
    [
        ("eps_forward", "analyst"),
        ("normalized_eps", "analyst"),
        ("ebit_normalized_scale", "fundamental"),
        ("ebt_actual_scale", "fundamental"),
        ("total_assets_scale", "fundamental"),
        ("total_assets", "fundamental"),
    ],
)
def test_semantic_tokens_override_dataset_prefix(prefix, suffix, category):
    field = f"{prefix}_{suffix}"
    assert classify_leaf(field) == category
    verdict = validate_expression(f"rank({field})")
    assert verdict["status"] == "violation"
    assert verdict["blocked"] == [field]
    assert dispatch_block_reason(verdict) is not None


@pytest.mark.parametrize("field", ["pv106_steps_count", "pv106_ebitwise", "opt3_epslike", "pv106_assetsproxy"])
def test_semantic_tokens_do_not_match_inside_longer_words(field):
    assert validate_expression(f"rank({field})")["status"] == "ok"


@pytest.mark.parametrize("field", ["pv87_eps_forward", "pv87_total_assets_scale"])
def test_submission_refuses_semantic_violation_before_mutation(field, monkeypatch):
    from types import SimpleNamespace

    from core.db import connect, init_tables
    from runner.submit import flow

    conn = connect(":memory:")
    try:
        init_tables(conn)
        conn.execute("INSERT INTO alpha_results (alpha_id,status,raw_json) VALUES ('scope-test','UNSUBMITTED','{}')")
        conn.commit()
        session = SimpleNamespace(
            get=lambda *args, **kwargs: SimpleNamespace(json=lambda: {"regular": {"code": f"rank({field})"}})
        )
        monkeypatch.setattr(flow, "ensure_description", lambda *args: pytest.fail("scope violation reached PATCH"))
        monkeypatch.setattr(flow, "try_submit", lambda *args: pytest.fail("scope violation reached POST"))
        assert flow.check_and_submit(session, conn, "scope-test") == "SCOPE_BLOCKED"
        assert (
            conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name='submission_requests'"
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()
