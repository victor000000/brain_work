"""The standing reads: threshold flags and the fragile-field split."""

import re

import pytest

from tests.test_storage.conftest import conn
from tools.reads import SHAPE_THRESHOLDS, mix_reads, shape_reads, wrap_read


def _alpha(c, aid, template, region="HKG", sh=2.0, expr="rank(close)", created="2026-10-13 10:00:00"):
    c.execute(
        "INSERT INTO alpha_results (alpha_id, expression, region, delay, is_sharpe, created_at, template) "
        "VALUES (?,?,?,1,?,?,?)",
        [aid, expr, region, sh, created, template],
    )


def test_shape_reads_flag_the_verdict_when_the_threshold_is_reached(capsys):
    c = conn()
    for i in range(SHAPE_THRESHOLDS["iv_skew_reversal"]):
        _alpha(c, f"IV{i}", "iv_skew_reversal", region="USA")
    _alpha(c, "LW0", "long_window_normalized")
    shape_reads(c)
    out = capsys.readouterr().out
    assert "INCONCLUSIVE: median gap" in out
    assert "1/100" in out, "long_window_normalized at one draw of its hundred"


def test_wrap_read_splits_on_the_fragile_pattern(capsys):
    c = conn()
    _alpha(c, "F1", "t", expr="rank(pv37_close_12)", created="2026-10-14 10:00:00")
    _alpha(c, "N1", "t", expr="rank(close)", created="2026-10-14 10:00:00")
    c.execute(
        "INSERT INTO check_failures (alpha_id, check_name, limit_val, actual_val, first_seen, last_seen, seen_count) "
        "VALUES ('F1', 'CONCENTRATED_WEIGHT', '0.1', '0.4', 'x', 'x', 1)"
    )
    wrap_read(c, "2026-10-12 00:00:00", "2026-10-15 03:00:00", "pre-wrap ")
    out = capsys.readouterr().out
    assert "fragile=True  n=  1  CW fails= 1  100%" in out
    assert "fragile=False n=  1  CW fails= 0  0%" in out


def test_mix_reads_reports_shares(capsys):
    c = conn()
    _alpha(c, "C1", "t", region="CHN", created="2026-10-06 10:00:00")
    _alpha(c, "H1", "t", created="2026-10-06 10:00:00")
    mix_reads(c)
    out = capsys.readouterr().out
    assert "CHN 1 (50.0%)" in out
    assert "HKG 1 (50.0%)" in out


def test_iv_threshold_counts_only_measured_usa_results(capsys):
    c = conn()
    try:
        for index in range(60):
            _alpha(c, f"OTHER{index}", "iv_skew_reversal", region="IND")
        for index in range(59):
            _alpha(c, f"USA{index}", "iv_skew_reversal", region="USA")
        _alpha(c, "MISSING", "iv_skew_reversal", region="USA", sh=None)
        shape_reads(c)
        line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("iv_skew_reversal"))
        assert "WAIT: 59/60 measured; 1 more needed" in line
    finally:
        c.close()


@pytest.mark.parametrize(
    "created,expected",
    [("2026-10-11T23:30:00-04:00", 1), ("2026-10-12T01:00:00+08:00", 0)],
)
def test_shape_window_uses_the_instant_in_utc(created, expected, capsys):
    c = conn()
    try:
        _alpha(c, "OFFSET", "long_window_normalized", created=created)
        shape_reads(c)
        assert re.search(rf"(?m)^long_window_normalized\s+{expected}\b", capsys.readouterr().out)
    finally:
        c.close()


def test_backfill_boundary_is_utc_and_end_exclusive(capsys):
    c = conn()
    try:
        _alpha(c, "BEFORE", "t", expr="rank(pv37_close_12)", created="2026-10-14T22:59:59-04:00")
        _alpha(c, "AFTER", "t", expr="rank(pv37_close_12)", created="2026-10-14T23:00:00-04:00")
        c.execute(
            "INSERT INTO check_failures (alpha_id,check_name,first_seen,last_seen,seen_count) "
            "VALUES ('BEFORE','CONCENTRATED_WEIGHT','x','x',1)"
        )
        wrap_read(c, "2026-10-12 00:00:00", "2026-10-15 03:00:00", "pre-wrap ")
        wrap_read(c, "2026-10-15 03:00:00", None, "post-wrap")
        output = capsys.readouterr().out
        assert "pre-wrap   fragile=True  n=  1  CW fails= 1  100%" in output
        assert "post-wrap  fragile=True  n=  1  CW fails= 0  0%" in output
    finally:
        c.close()


def test_region_mix_does_not_count_the_next_utc_day_as_pre_tilt(capsys):
    c = conn()
    try:
        _alpha(c, "BEFORE", "t", region="CHN", created="2026-10-11T19:59:59-04:00")
        _alpha(c, "AFTER", "t", region="HKG", created="2026-10-11T20:00:00-04:00")
        mix_reads(c)
        output = capsys.readouterr().out
        assert "pre-tilt (10-05..10-12): n=1  CHN 1 (100.0%)  HKG 0 (0.0%)" in output
        assert "pre-5x-tilt (10-12..10-15): n=1  CHN 0 (0.0%)  HKG 1 (100.0%)" in output
    finally:
        c.close()


def test_shape_read_uses_the_median_of_both_middle_values(capsys):
    c = conn()
    try:
        _alpha(c, "LOW", "long_window_normalized", sh=-0.4)
        _alpha(c, "HIGH", "long_window_normalized", sh=0.2)
        shape_reads(c)
        assert re.search(r"(?m)^long_window_normalized\s+2\s+-0\.100\b", capsys.readouterr().out)
    finally:
        c.close()


def test_read_tool_can_share_a_snapshot_with_another_reader(tmp_path, monkeypatch):
    from core.db import connect
    from tools import reads

    path = str(tmp_path / "snapshot.duckdb")
    writer = connect(path)
    writer.execute("CREATE TABLE example (id INTEGER)")
    writer.close()
    reader = connect(path, read_only=True)
    monkeypatch.setattr("sys.argv", ["reads", "--db", path])
    monkeypatch.setattr(reads, "shape_reads", lambda c: None)
    monkeypatch.setattr(reads, "wrap_read", lambda *a: None)
    monkeypatch.setattr(reads, "mix_reads", lambda c: None)
    try:
        assert reads.main() == 0
        assert reader.execute("SELECT COUNT(*) FROM example").fetchone() == (0,)
    finally:
        reader.close()
