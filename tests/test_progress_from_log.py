"""Log-based progress reporting (works while the explorer holds the DB)."""

from tests.test_progress_from_log_helpers import ALPHA_OK, ALPHA_WEAK, _write, logdir
from tools import progress_from_log as p

# The fixture is re-exported: pytest finds it by name in this module's namespace.
__all__ = ["logdir"]


def test_parses_stored_alphas(logdir):
    _write(logdir, "alpha.log", [ALPHA_OK, ALPHA_WEAK])
    data = p.collect("2026-10-05")
    assert [r["id"] for r in data["alphas"]] == ["j281Ndo9", "xAbRXmVl"]
    assert data["alphas"][0]["uni"] == "TOPSP500"
    assert data["alphas"][0]["delay"] == "1"
    assert data["alphas"][0]["neut"] == "SLOW"


def test_ignores_other_days(logdir):
    _write(logdir, "alpha.log", [ALPHA_OK.replace("2026-10-05", "2026-10-04")])
    assert p.collect("2026-10-05")["alphas"] == []


def test_reads_the_rotated_file_too(logdir):
    """A past day lives in alpha.log.<day> once the log has rotated."""
    _write(logdir, "alpha.log.2026-10-04", [ALPHA_OK.replace("2026-10-05", "2026-10-04")])
    assert len(p.collect("2026-10-04")["alphas"]) == 1


def test_gate_uses_the_region_sharpe_floor():
    ok = {"region": "USA", "sh": "1.60", "fi": "1.0", "to": "0.10", "ts_": "0.50"}
    assert p.passes_gate(ok)
    # CHN carries a higher floor (2.07), measured from the platform's own limits.
    assert not p.passes_gate({**ok, "region": "CHN"})
    assert p.passes_gate({**ok, "region": "CHN", "sh": "2.10"})
    # fitness floor and turnover band
    assert not p.passes_gate({**ok, "fi": "0.99"})
    assert not p.passes_gate({**ok, "to": "0.005"})
    assert not p.passes_gate({**ok, "to": "0.71"})


def test_gate_applies_the_out_of_sample_floor():
    """`eligibility_clause` requires `test_sharpe > 0`, so the report must too.

    Without it the count includes alphas the selector will never pick — the
    flattering direction. The clearest case: 0mrYmzEp, IS sharpe 8.29 and a
    test sharpe of 0.00.
    """
    ok = {"region": "USA", "sh": "8.29", "fi": "22.74", "to": "0.40", "ts_": "0.00"}
    assert not p.passes_gate(ok)
    assert not p.passes_gate({**ok, "ts_": "-1.20"})
    assert p.passes_gate({**ok, "ts_": "0.01"})
