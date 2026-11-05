"""cnhkmcp staleness template — alpha / (1 + days_from_last_change)."""


def staleness_decay(f1, f2):
    """cnhkmcp: alpha / (1 + days_from_last_change) — freshness."""
    return f"rank(rank({f1}) / (1 + days_from_last_change({f2})))"
