"""Store alpha simulation results to DB."""

from __future__ import annotations

import json

from core.log import get_file_logger
from storage.probe_attribution import probe_template
from storage.store_alpha_extract import extract_row, log_alpha
from storage.track_ops import track_operator_usage, untrack_operator_usage
from storage.track_pyramid import derive_pyramid_categories, load_field_to_category
from storage.track_templates import identify_template, record_template_performance

alog = get_file_logger("alpha")

_FIELD_CAT_CACHE: dict[str, str] | None = None


def _field_to_category(conn):
    """Load and cache the field->category map. Cache lives for the process
    lifetime — new fields downloaded mid-run are not picked up until restart,
    matching the behavior of the existing field/dataset bootstrap."""
    global _FIELD_CAT_CACHE
    if _FIELD_CAT_CACHE is None:
        _FIELD_CAT_CACHE = load_field_to_category(conn)
    return _FIELD_CAT_CACHE


def store_alpha(conn, sim_id, expr, region, universe, delay, settings, data):
    """Store a completed alpha's stats to alpha_results table."""
    alog.debug("Storing alpha %s sim=%s %s/%s", data.get("id"), sim_id, region, universe)
    language = settings.get("language", "FASTEXPR")
    template = probe_template(conn, sim_id, expr) or (
        "python:unclassified" if language == "PYTHON" else identify_template(expr)
    )
    if language == "PYTHON":
        # Only declared input fields count; comments and helper variable names
        # must not attribute unrelated dataset categories to a Python alpha.
        from runner.python_probe_source import validate_python_source

        categories = _field_to_category(conn)
        try:
            fields = validate_python_source(expr, set(categories))
        except ValueError:
            fields = ()  # Retain the result even for source outside the pilot grammar.
        pyramid_categories = derive_pyramid_categories(" ".join(fields), categories)
    else:
        pyramid_categories = derive_pyramid_categories(expr, _field_to_category(conn))
    data = {**data, "_submitted_settings": dict(settings)}
    row = (
        *extract_row(sim_id, expr, region, universe, delay, settings, data),
        template,
        pyramid_categories,
    )

    # Idempotent operator accounting: subtract what this alpha was previously
    # credited for before adding the new expression's operators.
    old = conn.execute(
        "SELECT expression, region, raw_json FROM alpha_results WHERE alpha_id=?",
        (data.get("id"),),
    ).fetchone()
    old_language = "FASTEXPR"
    if old and old[2]:
        previous = json.loads(old[2])
        old_language = (previous.get("_submitted_settings") or previous.get("settings") or {}).get(
            "language", "FASTEXPR"
        )
    if old and old[0] and old_language == "FASTEXPR":
        untrack_operator_usage(conn, old[0], old[1])

    conn.execute(
        """
        INSERT INTO alpha_results
        (alpha_id, sim_id, expression, region, universe, delay,
         neutralization, decay, truncation,
         is_sharpe, is_fitness, is_turnover, is_returns,
         is_drawdown, is_margin, is_pnl,
         is_long_count, is_short_count,
         train_sharpe, train_fitness,
         test_sharpe, test_fitness,
         is_rn_sharpe, is_rn_fitness,
         grade, status, operator_count, raw_json, created_at,
         template, pyramid_categories)
        VALUES (?,?,?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?, ?,?, ?,?, ?,?, ?,?,
                ?,?,?,?,?, ?, ?)
        ON CONFLICT(alpha_id) DO UPDATE SET
            sim_id=excluded.sim_id, expression=excluded.expression,
            region=excluded.region, universe=excluded.universe, delay=excluded.delay,
            neutralization=excluded.neutralization, decay=excluded.decay,
            truncation=excluded.truncation,
            is_sharpe=excluded.is_sharpe, is_fitness=excluded.is_fitness,
            is_turnover=excluded.is_turnover, is_returns=excluded.is_returns,
            is_drawdown=excluded.is_drawdown, is_margin=excluded.is_margin,
            is_pnl=excluded.is_pnl,
            is_long_count=excluded.is_long_count, is_short_count=excluded.is_short_count,
            train_sharpe=excluded.train_sharpe, train_fitness=excluded.train_fitness,
            test_sharpe=excluded.test_sharpe, test_fitness=excluded.test_fitness,
            is_rn_sharpe=excluded.is_rn_sharpe, is_rn_fitness=excluded.is_rn_fitness,
            grade=excluded.grade,
            -- Local submission status is terminal once set; a re-store of the
            -- platform's own 'UNSUBMITTED' must not clobber it.
            status=CASE WHEN alpha_results.status IN ('SUBMITTED','REJECTED')
                        THEN alpha_results.status ELSE excluded.status END,
            operator_count=excluded.operator_count, raw_json=excluded.raw_json,
            created_at=excluded.created_at,
            template=excluded.template, pyramid_categories=excluded.pyramid_categories
    """,
        row,
    )

    if language == "FASTEXPR":
        track_operator_usage(conn, expr, region)

    is_stats = data.get("is") or {}
    test = data.get("test") or {}
    sharpe = is_stats.get("sharpe", 0) or 0
    test_sh = test.get("sharpe", 0) or 0
    fitness = is_stats.get("fitness", 0) or 0
    record_template_performance(conn, expr, data.get("id"), sharpe, test_sh, fitness, template_name=template)

    conn.commit()
    log_alpha(data, sharpe, test_sh, fitness, is_stats, region, universe, delay, settings, expr)
