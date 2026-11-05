"""The durable expression -> template ledger: survives eviction and restarts.

The in-memory map covered 2,000 draws — under half a day of generation — so an
alpha stored when its simulation finished could find its entry evicted, or its
process gone, and fall to the legacy signature list (or "unknown"). The ledger
is one `name\\texpr` line per draw, folded back in on first use.
"""

import pytest

import generator.weighted_selection.state as st
from storage.track_templates import identify_template


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "expr_templates.tsv"
    monkeypatch.setenv("BRAIN_EXPR_TEMPLATE_PATH", str(path))
    st.set_state(st.UsageState())
    yield path
    st.set_state(st.UsageState())  # leave a clean singleton for other tests


def test_record_writes_the_ledger_and_peek_reads_it(ledger):
    st.record_expr_template("rank(close)", "some_shape")
    assert "some_shape\trank(close)" in ledger.read_text()
    assert st.peek_expr_template("rank(close)") == "some_shape"


def test_a_restart_still_resolves_the_label(ledger):
    st.record_expr_template("hump(rank(x), hump=0.05)", "hump_turnover_controlled")
    st.set_state(st.UsageState())  # the process died; nothing in memory
    assert st.peek_expr_template("hump(rank(x), hump=0.05)") == "hump_turnover_controlled"


def test_the_loader_keeps_only_the_tail(ledger, monkeypatch):
    monkeypatch.setattr(st, "MAX_TRACKED_EXPRESSIONS", 3)
    for i in range(5):
        st.record_expr_template(f"expr_{i}", f"shape_{i}")
    st.set_state(st.UsageState())
    assert st.peek_expr_template("expr_4") == "shape_4"
    assert st.peek_expr_template("expr_0") is None


def test_identify_template_uses_the_ledger_after_a_restart(ledger):
    """The end the gap was found at: attribution for a stored alpha."""
    st.record_expr_template("ts_ir(returns, 120)", "ts_ir_trend")
    st.set_state(st.UsageState())
    assert identify_template("ts_ir(returns, 120)") == "ts_ir_trend"


def test_a_missing_ledger_is_silent(ledger):
    assert st.peek_expr_template("anything") is None  # no file written yet


@pytest.mark.parametrize(
    "expression",
    ['def alpha():\r\n\treturn "路径\\\\value"\n', '@json:"literal"'],
)
def test_encoded_expression_survives_restart_with_legacy_entries(ledger, expression):
    st.record_expr_template("rank(close)", "legacy")
    st.record_expr_template(expression, "python_source")
    assert len(ledger.read_text().splitlines()) == 2
    st.set_state(st.UsageState())
    assert st.peek_expr_template(expression) == "python_source"
    assert st.peek_expr_template("rank(close)") == "legacy"


def test_malformed_encoded_entries_do_not_break_reload(ledger):
    ledger.write_text("bad\t@json:{\nbad\t@json:[]\nvalid\trank(close)\n")
    st.set_state(st.UsageState())
    assert st.peek_expr_template("rank(close)") == "valid"
    assert len(st.get_state().expr_templates) == 1


def test_a_popped_entry_is_recovered_from_the_ledger(ledger, monkeypatch):
    """The measured case behind the reload: a slotless constant is recorded,
    popped by `_release` when a 4-field build uses it as a half, and its alpha
    is stored minutes later. The map no longer holds it, and the first version
    of the loader — one read per process — would never look again. Nine alphas
    in the first two hours of 2026-10-14 went `unknown` exactly this way.
    """
    monkeypatch.setattr(st, "LEDGER_RELOAD_SEC", 0)
    st.record_expr_template("(close - vwap) / vwap", "vwap_close_spread")
    assert st.lookup_expr_template("(close - vwap) / vwap") == "vwap_close_spread"  # the pop
    assert st.peek_expr_template("(close - vwap) / vwap") == "vwap_close_spread"


def test_an_entry_from_another_process_lands_after_the_ttl(ledger, monkeypatch):
    monkeypatch.setattr(st, "LEDGER_RELOAD_SEC", 9999)
    assert st.peek_expr_template("warm the loader") is None
    with open(ledger, "a") as fh:  # as another process would
        fh.write("hump_turnover_controlled\thump(rank(x), hump=0.05)\n")
    assert st.peek_expr_template("hump(rank(x), hump=0.05)") is None  # within the TTL
    st.get_state().ledger_loaded_at = 0.0  # the TTL elapses
    assert st.peek_expr_template("hump(rank(x), hump=0.05)") == "hump_turnover_controlled"
