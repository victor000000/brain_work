"""Summary + prune-recommendation reports."""

from tools.probe_simulation_combos._log import log


def report_summary(results):
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    by_verdict = {}
    for r in results:
        by_verdict.setdefault(r["verdict"], []).append(r)
    for verdict in sorted(by_verdict):
        log.info("%s: %d", verdict, len(by_verdict[verdict]))
        for r in by_verdict[verdict]:
            log.info("  %s/%s/d%d", r["region"], r["universe"], r["delay"])


def _fmt(r):
    return f"{r['region']}/{r['universe']}/d{r['delay']}"


def report_rejects(results):
    """Split real rejections from probe failures.

    An HTTP_* verdict means the probe never got an answer from the API — a 500,
    a 429, an auth problem — not that BRAIN rejected the combo. Recommending a
    prune on those would delete valid region/universe pairs.
    """
    rejects = [r for r in results if r["verdict"].startswith("REJECT")]
    failed = [r for r in results if r["verdict"].startswith("HTTP_") or r["verdict"] == "RATE_LIMITED"]

    if rejects:
        log.info("-" * 60)
        log.info("REJECTED by BRAIN — prune these from core.regions.REGION_CONFIGS:")
        for r in rejects:
            log.info('  ("%s", "%s", %d),  # %s', r["region"], r["universe"], r["delay"], r["verdict"])

    if failed:
        log.info("-" * 60)
        log.info("PROBE FAILED (HTTP error) — retry these; they are NOT rejections:")
        for r in failed:
            log.info("  %s  %s", _fmt(r), r["verdict"])
