"""Human-readable reports rendered to the logger after a snapshot."""

from tools.pyramid_status._config import ACTIVE_THRESHOLD
from tools.pyramid_status._log import log


def report_top_multipliers(multipliers, top_n=25):
    """Print the top-N pyramids by multiplier."""
    log.info("=" * 60)
    log.info("PYRAMID STATUS (top %d by multiplier)", top_n)
    log.info("=" * 60)
    sorted_mult = sorted(multipliers, key=lambda m: -m.get("multiplier", 0))
    for m in sorted_mult[:top_n]:
        cid = (m.get("category") or {}).get("id")
        active = "ACTIVE" if m.get("multiplier", 0) > ACTIVE_THRESHOLD else "baseline"
        log.info("  %-20s %s/d%s  mult=%.2f  [%s]", cid, m.get("region"), m.get("delay"), m.get("multiplier"), active)


def report_alphas_per_pyramid(pyramid_to_alphas, attributions):
    """Print user's alphas grouped by pyramid (active pyramids only)."""
    if not pyramid_to_alphas:
        return
    log.info("=" * 60)
    log.info("ALPHAS PER PYRAMID (active pyramids only)")
    log.info("=" * 60)
    pname_mult = {}
    for attr in attributions:
        pname_mult.setdefault(attr["pyramid_name"], attr["multiplier"])
    for pname in sorted(pyramid_to_alphas, key=lambda p: -(pname_mult.get(p, 0) or 0)):
        mult = pname_mult.get(pname, 0) or 0
        if mult <= ACTIVE_THRESHOLD:
            continue
        alphas = pyramid_to_alphas[pname]
        log.info("  %-25s mult=%.2f  alphas=%d", pname, mult, len(alphas))
        for a in alphas[:8]:
            sharpe_s = f"{a['sharpe']:.2f}" if a["sharpe"] is not None else "?"
            log.info("    %s status=%s sharpe=%s", a["id"], a["status"], sharpe_s)


def report_uncovered_active(multipliers, pyramid_to_alphas):
    """Print active pyramids the user has zero alphas in (opportunity surface)."""
    active_names = {
        f"{m['region']}/D{m['delay']}/{(m.get('category') or {}).get('id', '').upper()}"
        for m in multipliers
        if m.get("multiplier", 0) > ACTIVE_THRESHOLD
    }
    covered = set(pyramid_to_alphas)
    uncovered = sorted(active_names - covered)
    if not uncovered:
        return
    log.info("=" * 60)
    log.info("UNCOVERED ACTIVE PYRAMIDS (no alphas — opportunity)")
    log.info("=" * 60)
    for name in uncovered:
        log.info("  %s", name)
