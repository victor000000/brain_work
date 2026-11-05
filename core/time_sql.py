"""UTC instants for stored platform ISO timestamps and project UTC text."""


def utc_timestamp_sql(column: str) -> str:
    """SQL TIMESTAMP in UTC for a trusted text column, independent of DB time zone.

    Platform offsets describe an instant; bare project timestamps and dates are
    already UTC. Both branches return a timezone-free UTC timestamp, so fetching
    results does not require the driver's optional Python timezone packages.
    Invalid or absent timestamps become NULL rather than entering a window.
    """
    zone_suffix = r"(Z| UTC|[+-][0-9]{2}(:?[0-9]{2})?)$"
    return (
        f"(CASE WHEN length(trim({column})) > 10 AND regexp_matches(trim({column}), '{zone_suffix}') "
        f"THEN (TRY_CAST({column} AS TIMESTAMPTZ) AT TIME ZONE 'UTC') "
        f"ELSE TRY_CAST({column} AS TIMESTAMP) END)"
    )
