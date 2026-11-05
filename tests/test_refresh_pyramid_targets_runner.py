"""refresh_pyramid_targets runner: --dry-run must win over --apply."""

import argparse


def _stub_runner(monkeypatch, *, apply, dry_run):
    """Wire runner.main() to a no-network pipeline that records writes."""
    from tools.refresh_pyramid_targets import runner

    writes = []
    monkeypatch.setattr(
        runner,
        "_parse_args",
        lambda: argparse.Namespace(period="current", apply=apply, dry_run=dry_run),
    )
    monkeypatch.setattr(runner, "get_session", lambda: None)
    monkeypatch.setattr(runner, "fetch_pyramid_alphas", lambda *a: [])
    monkeypatch.setattr(runner, "fetch_pyramid_multipliers", lambda *a: [])
    monkeypatch.setattr(runner, "quarter_bounds", lambda: ("2026-07-01", "2026-09-30"))
    monkeypatch.setattr(runner, "compute_targets", lambda *a: [])
    monkeypatch.setattr(runner, "report_distribution", lambda *a: None)
    monkeypatch.setattr(runner, "report_top_priority", lambda *a: None)
    monkeypatch.setattr(
        runner,
        "upsert",
        lambda rows: writes.append(rows) or {"history": 0, "current": 0, "archived": 0},
    )
    return runner, writes


def test_dry_run_wins_over_apply(monkeypatch):
    """`--apply --dry-run` is contradictory; the safe flag must win."""
    runner, writes = _stub_runner(monkeypatch, apply=True, dry_run=True)
    runner.main()
    assert writes == []


def test_apply_without_dry_run_does_write(monkeypatch):
    """Positive control: the dry-run guard must not block a real --apply."""
    runner, writes = _stub_runner(monkeypatch, apply=True, dry_run=False)
    runner.main()
    assert writes == [[]]
