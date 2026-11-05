"""Distribution + top-priority log output for refresh_pyramid_targets."""

from tools.refresh_pyramid_targets._log import log


def report_distribution(rows):
    """Bucket the computed rows by alpha_count for a quick gap overview."""
    completed = sum(1 for r in rows if r["alpha_count"] >= 3)
    need1 = sum(1 for r in rows if r["alpha_count"] == 2)
    need2 = sum(1 for r in rows if r["alpha_count"] == 1)
    uncovered = sum(1 for r in rows if r["alpha_count"] == 0)
    log.info("Distribution:")
    log.info("  completed (>=3): %d", completed)
    log.info("  2 alphas (need +1): %d", need1)
    log.info("  1 alpha  (need +2): %d", need2)
    log.info("  uncovered: %d", uncovered)


def report_top_priority(rows, top_n=10):
    """Show the highest-score (region, delay, category) tuples."""
    log.info("Top %d highest-priority pyramids:", top_n)
    for r in sorted(rows, key=lambda r: -r["score"])[:top_n]:
        log.info(
            "  %s/D%d/%s  alphas=%d  mult=%.2f  gap=%d  score=%.2f",
            r["region"],
            r["delay"],
            r["category"].upper(),
            r["alpha_count"],
            r["multiplier"],
            r["gap_to_3"],
            r["score"],
        )
