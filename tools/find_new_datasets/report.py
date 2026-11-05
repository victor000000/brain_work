"""Reports for find_new_datasets — flagged subcategories + found dataset IDs."""

from tools.find_new_datasets._log import log


def report_flagged(flagged, cached_counts):
    log.info("-" * 60)
    log.info("Subcategories to scan: %d", len(flagged))
    for sid, name, old, new, delta in flagged:
        marker = "NEW" if old == 0 and sid not in cached_counts else f"+{delta}"
        log.info("  [%s] %s (%s): %d -> %d", marker, sid, name, old, new)
    log.info("-" * 60)


def report_findings(found, total_calls):
    log.info("=" * 60)
    log.info("Scan complete: %d API calls, %d new dataset IDs found", total_calls, len(found))
    if not found:
        log.info("(Subcategory counts grew but no new dataset IDs surfaced on page 1.")
        log.info(" New datasets may exist beyond page 1 — run full refresh to confirm.)")
    else:
        log.info("-" * 60)
        for did in sorted(found):
            e = found[did]
            combos = sorted(set(e["seen"]))
            sample = ", ".join(f"{r}/{u}/d{d}" for r, u, d in combos[:3])
            more = f" (+{len(combos) - 3} more)" if len(combos) > 3 else ""
            log.info("  %s | %s | subcat=%s | seen in: %s%s", did, e["name"], e["subcategory"], sample, more)
    log.info("=" * 60)
