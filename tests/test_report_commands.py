"""Report entry points must read concurrently and use recorded submission state."""

import sys

import pytest

from core.db import connect, connect_for_reading, init_tables
from tools import progress_report, registry_sweep, template_report


@pytest.fixture
def snapshot(tmp_path):
    path = str(tmp_path / "snapshot.duckdb")
    conn = connect(path)
    init_tables(conn)
    conn.executemany(
        "INSERT INTO alpha_results "
        "(alpha_id,template,expression,region,delay,status,created_at,is_sharpe) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("IN", "included", "rank(close)", "USA", 1, "SUBMITTED", "2026-10-11T20:00:00-04:00", None),
            ("OUT", "excluded", "rank(close)", "USA", 1, "SUBMITTED", "2026-10-12T01:00:00+08:00", 2.0),
            ("NEXT", "excluded", "rank(close)", "USA", 1, "UNSUBMITTED", "2026-10-12T20:00:00-04:00", 2.0),
            ("OLD_STATUS", "included", "rank(close)", "USA", 1, "ACCEPTED", "2026-10-12 01:00:00 UTC", 2.0),
        ],
    )
    conn.execute(
        "INSERT INTO check_failures (alpha_id,check_name,first_seen,last_seen) VALUES ('OUT','OUTSIDE','x','x')"
    )
    conn.close()
    reader = connect_for_reading(path)
    try:
        yield path, reader
    finally:
        reader.close()


def test_progress_uses_submitted_and_the_selected_utc_creation_day(snapshot, capsys):
    path, reader = snapshot
    assert progress_report.main(["--db", path, "--day", "2026-10-12"]) == 0
    output = capsys.readouterr().out
    assert "Stored alpha results: 4" in output
    assert "Recorded submissions: 2" in output
    assert "Created 2026-10-12 UTC: 2 alpha results, 1 recorded submissions" in output
    assert "IN: sharpe=n/a, fitness=n/a" in output
    assert "OLD_STATUS:" not in output
    assert reader.execute("SELECT count(*) FROM alpha_results").fetchone()[0] == 4


def test_template_report_shares_snapshot_and_normalizes_cutoff(snapshot, monkeypatch, capsys):
    path, _ = snapshot
    monkeypatch.setattr(sys, "argv", ["template_report", "--db", path, "--since", "2026-10-12"])
    assert template_report.main() == 0
    output = capsys.readouterr().out
    assert "included" in output
    assert "OUTSIDE" not in output
    assert "excluded" in output  # NEXT is on the next UTC day, still after the cutoff.
    assert "50.0%" in output  # The two included rows have one measured floor hit.


def test_registry_sweep_shares_snapshot(snapshot, monkeypatch, capsys):
    path, _ = snapshot

    def example(fields, rng):
        return "rank(close)"

    monkeypatch.setattr(sys, "argv", ["registry_sweep", "--db", path, "--renders", "1"])
    monkeypatch.setattr(registry_sweep, "ALL_TEMPLATES", [(example, ["rank"])])
    monkeypatch.setattr(registry_sweep, "REGION_CONFIGS", [("USA", "TOP1000", 1)])
    monkeypatch.setattr(registry_sweep, "load_all_fields", lambda *args: None)
    monkeypatch.setattr(registry_sweep, "prepare_pools", lambda conn: ({}, ["close"], set(), set(), {"rank"}, 0))
    monkeypatch.setattr(registry_sweep, "template_uses_pool", lambda fn: True)
    assert registry_sweep.main() == 0
    assert "invalid renders        : 0" in capsys.readouterr().out
