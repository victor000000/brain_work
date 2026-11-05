"""Population definitions for the portfolio KPI report."""

POPULATIONS = [
    ("Hits (is_sharpe >= 1.0)", "is_sharpe >= 1.0"),
    (
        "Submit attempts (SUBMITTED + REJECTED + THROTTLED)",
        "status IN ('SUBMITTED', 'REJECTED', 'THROTTLED')",
    ),
]
