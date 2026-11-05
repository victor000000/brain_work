"""Print simulation summary from DB."""

import logging

log = logging.getLogger("brain")


def print_summary(conn):
    """Print final simulation results."""
    alphas = conn.execute("SELECT COUNT(*) FROM alpha_results").fetchone()[0]
    ok = conn.execute("SELECT COUNT(*) FROM simulations WHERE status='COMPLETE' AND parent_id IS NOT NULL").fetchone()[
        0
    ]
    errs = conn.execute(
        "SELECT COUNT(*) FROM simulations WHERE status IN ('ERROR','FAIL','CANCELLED') AND parent_id IS NOT NULL"
    ).fetchone()[0]
    log.info("=== DONE: %d alphas saved, %d ok, %d err ===", alphas, ok, errs)

    # Top alphas by in-sample Sharpe
    top = conn.execute(
        "SELECT expression, region, neutralization, is_sharpe, is_fitness, test_sharpe "
        "FROM alpha_results WHERE is_sharpe IS NOT NULL "
        "ORDER BY is_sharpe DESC LIMIT 10"
    ).fetchall()
    for expr, reg, neut, sh, fi, tsh in top:
        log.info("  %s neut=%s sh=%.2f fi=%.2f ts=%.2f  %s", reg, neut, sh or 0, fi or 0, tsh or 0, expr[:50])

    # Per-region breakdown
    for reg, cnt in conn.execute("SELECT region, COUNT(*) FROM alpha_results GROUP BY region").fetchall():
        log.info("  %s: %d alphas", reg, cnt)

    # Error breakdown
    err_msgs = conn.execute(
        "SELECT error_message, COUNT(*) FROM simulations "
        "WHERE error_message IS NOT NULL GROUP BY error_message "
        "ORDER BY COUNT(*) DESC LIMIT 5"
    ).fetchall()
    if err_msgs:
        log.info("Top errors:")
        for msg, cnt in err_msgs:
            log.info("  [%dx] %s", cnt, msg[:80])
