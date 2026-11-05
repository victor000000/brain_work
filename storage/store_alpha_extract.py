"""Row extraction and logging helpers for alpha storage."""

import json
import logging

from core.log import get_file_logger

log = logging.getLogger("brain")
alog = get_file_logger("alpha")


def extract_row(sim_id, expr, region, universe, delay, settings, data):
    """Build the alpha_results row tuple from API response data."""
    is_stats = data.get("is") or {}
    train = data.get("train") or {}
    test = data.get("test") or {}
    risk_neut = is_stats.get("riskNeutralized") or {}
    regular = data.get("regular") or {}

    return (
        data.get("id"),
        sim_id,
        expr,
        region,
        universe,
        delay,
        settings.get("neutralization"),
        settings.get("decay"),
        settings.get("truncation"),
        is_stats.get("sharpe"),
        is_stats.get("fitness"),
        is_stats.get("turnover"),
        is_stats.get("returns"),
        is_stats.get("drawdown"),
        is_stats.get("margin"),
        is_stats.get("pnl"),
        is_stats.get("longCount"),
        is_stats.get("shortCount"),
        train.get("sharpe"),
        train.get("fitness"),
        test.get("sharpe"),
        test.get("fitness"),
        risk_neut.get("sharpe"),
        risk_neut.get("fitness"),
        data.get("grade"),
        data.get("status"),
        regular.get("operatorCount"),
        json.dumps(data),
        data.get("dateCreated"),
    )


def log_alpha(data, sharpe, test_sh, fitness, is_stats, region, universe, delay, settings, expr):
    """Log alpha results and flag high-quality alphas."""
    turnover = is_stats.get("turnover", 0) or 0
    rn_sh = (is_stats.get("riskNeutralized") or {}).get("sharpe", 0) or 0

    alog.info(
        "alpha=%s sh=%.2f ts=%.2f fi=%.2f to=%.4f rn=%.2f %s/%s/d%d n=%s",
        data.get("id"),
        sharpe,
        test_sh,
        fitness,
        turnover,
        rn_sh,
        region,
        universe,
        delay,
        settings.get("neutralization"),
    )
    # A *prefix*, not the expression: the community-derived shapes are 200-250
    # characters, so this shows the outer wrapper and hides the operator that
    # identifies the shape — `dual_bucket_neutralized` keeps
    # `group_cartesian_product` past the cut, and a log-based count read it as
    # producing nothing while the database held ten. Attribute shapes by
    # `alpha_results.template` (`tools/template_report.py`), never by matching
    # this line, or the bias runs against exactly the long shapes.
    alog.debug("  expr=%s", expr[:80])

    if sharpe > 1.0 and test_sh > 0.5:
        aid = data.get("id")
        # Use INFO so good-news lines don't propagate into errors.log alongside
        # real warnings/errors. The aggregate `log` already uses info-level.
        alog.info("HIGH QUALITY %s: sh=%.2f ts=%.2f fi=%.2f %s/%s", aid, sharpe, test_sh, fitness, region, universe)
        log.info("HIGH QUALITY alpha %s: sh=%.2f ts=%.2f %s/%s", aid, sharpe, test_sh, region, universe)
