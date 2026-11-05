"""Count-based weights: weight = 1 / (1 + count). Inverse-coverage explorer.

Alphas are filtered to the ones the generator can still produce: every entry in
`pyramid_categories` must be pv or option. Of 179,377 stored alphas only 15,396
(8.6%) qualify — the rest involve model, analyst, fundamental, news or other
data that the pv/option restriction put out of reach. Unfiltered weights steer
selection using a population that is 91% unreachable.

An alpha whose category metadata is missing or malformed cannot be confirmed
reachable, so it is excluded rather than assumed good.
"""

# The only categories the generator draws on.
ALLOWED_CATEGORIES = ("pv", "option")

_ALLOWED_SQL = ", ".join(f"'{c}'" for c in ALLOWED_CATEGORIES)

# Reachable = has a category list, it parses, and nothing in it is outside
# ALLOWED_CATEGORIES. json_valid guards json_each, which errors on bad input.
# json_each's `value` is JSON-typed in DuckDB, so it must be unwrapped with
# json_extract_string — comparing it directly to 'pv' makes DuckDB try to
# parse 'pv' as JSON.
_REACHABLE_SQL = f"""
    pyramid_categories IS NOT NULL
    AND json_valid(pyramid_categories)
    AND NOT EXISTS (
        SELECT 1 FROM json_each(alpha_results.pyramid_categories)
        WHERE json_extract_string(value, '$') NOT IN ({_ALLOWED_SQL})
    )
"""


def _filter(pv_option_only: bool) -> str:
    return f"WHERE {_REACHABLE_SQL}" if pv_option_only else ""


def _where(pv_option_only: bool, extra: str = "") -> str:
    """Combine the reachability filter with an optional additional predicate."""
    clause = _REACHABLE_SQL if pv_option_only else ""
    if clause and extra:
        return f"WHERE {clause} AND {extra}"
    if clause:
        return f"WHERE {clause}"
    return f"WHERE {extra}" if extra else ""


def compute_weights(conn, column, pv_option_only=True):
    """1/(1+count) weight per distinct value of `column` in alpha_results."""
    rows = conn.execute(
        f"SELECT {column}, COUNT(*) FROM alpha_results {_filter(pv_option_only)} GROUP BY {column}"
    ).fetchall()
    return {value: 1.0 / (1.0 + count) for value, count in rows}


def compute_test_period_weights(conn, pv_option_only=True):
    """Test-period values live inside raw_json — extract as text, not JSON."""
    rows = conn.execute(
        "SELECT json_extract_string(raw_json, '$.settings.testPeriod') as tp, COUNT(*) "
        f"FROM alpha_results {_where(pv_option_only, 'raw_json IS NOT NULL')} GROUP BY tp"
    ).fetchall()
    return {tp or "P1Y6M": 1.0 / (1.0 + cnt) for tp, cnt in rows}


def compute_config_weights(conn, pv_option_only=True):
    """Per-config (region, universe, delay) inverse-coverage weight."""
    rows = conn.execute(
        "SELECT region, universe, delay, COUNT(*) FROM alpha_results "
        f"{_filter(pv_option_only)} GROUP BY region, universe, delay"
    ).fetchall()
    return {(region, universe, delay): 1.0 / (1.0 + count) for region, universe, delay, count in rows}
