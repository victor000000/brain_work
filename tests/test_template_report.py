"""The per-template report: floors, duration parsing and aggregation."""

from runner.submit.eligibility import REGION_DELAY_MIN_SHARPE
from tools.template_report import DEFAULT_FLOOR, duration_seconds, floor_for, format_row, summarize


def test_floor_for_reads_the_cell_table_and_defaults_elsewhere():
    (region, delay), value = next(iter(REGION_DELAY_MIN_SHARPE.items()))
    assert floor_for(region, delay) == value
    assert floor_for("NOPE", 9) == DEFAULT_FLOOR


def test_duration_seconds_parses_the_project_stamp_format():
    assert duration_seconds("2026-10-12 12:00:00 UTC", "2026-10-12 12:01:00 UTC") == 60
    # NULLs are the norm for rows written before 2026-10-12, and they must not raise.
    assert duration_seconds(None, "2026-10-12 12:01:00 UTC") is None
    assert duration_seconds("2026-10-12 12:00:00 UTC", None) is None
    assert duration_seconds("garbage", "2026-10-12 12:01:00 UTC") is None


def test_summarize_counts_alphas_floors_latencies_and_failures():
    alphas = [
        ("t_a", "NOPE", 9, 2.0),  # above the default floor
        ("t_a", "NOPE", 9, 1.0),  # below it
        ("t_a", "NOPE", 9, None),  # no sharpe recorded
        ("t_b", "NOPE", 9, 3.0),
    ]
    latencies = [("t_a", 100.0), ("t_a", 300.0), ("t_absent", 5.0)]
    failures = [("t_a", "LOW_2Y_SHARPE"), ("t_a", "LOW_2Y_SHARPE"), ("t_a", "PROD_CORRELATION")]

    acc = summarize(alphas, latencies, failures)

    assert acc["t_a"]["alphas"] == 3
    assert acc["t_a"]["at_floor"] == 1, "only the 2.0 clears the 1.58 default"
    assert sorted(acc["t_a"]["latencies"]) == [100.0, 300.0], "a latency for an absent template is dropped"
    assert acc["t_a"]["failures"] == {"LOW_2Y_SHARPE": 2, "PROD_CORRELATION": 1}
    assert acc["t_b"]["alphas"] == 1 and acc["t_b"]["failures"] == {}


def test_format_row_names_the_template_rate_and_top_failure():
    acc = summarize(
        [("t_a", "NOPE", 9, 2.0), ("t_a", "NOPE", 9, 1.0)],
        [("t_a", 120.0)],
        [("t_a", "LOW_2Y_SHARPE")],
    )
    line = format_row("t_a", acc["t_a"])
    assert line.startswith("t_a")
    assert "50.0%" in line, "one of two alphas at the floor"
    assert "LOW_2Y_SHARPE" in line
    assert "120s" in line
