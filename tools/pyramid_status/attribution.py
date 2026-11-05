"""Build per-alpha pyramid attribution rows from /alphas/{id} details."""

import time

from tools.pyramid_status._config import THROTTLE
from tools.pyramid_status._log import log
from tools.pyramid_status.fetch import fetch_alpha_pyramids


def build_attributions(session, alphas_by_status):
    """For each alpha, fetch detail and emit one attribution row per pyramid.

    Returns (attributions, pyramid_to_alphas):
      attributions:     list of dicts ready to upsert into pyramid_alpha_attribution.
      pyramid_to_alphas: dict[pyramid_name] -> list of summary dicts (for reports).
    """
    attributions = []
    pyramid_to_alphas = {}

    all_alphas = [a for xs in alphas_by_status.values() for a in xs]
    log.info("Fetching detail for %d alphas (pyramid attribution)", len(all_alphas))

    for i, a in enumerate(all_alphas):
        aid = a.get("id")
        if not aid:
            continue
        detail = fetch_alpha_pyramids(session, aid)
        if not detail:
            continue
        for pyr in detail["pyramids"]:
            attributions.append(
                {
                    "alpha_id": aid,
                    "pyramid_name": pyr.get("name"),
                    "multiplier": pyr.get("multiplier"),
                    "status": detail["status"],
                    "stage": detail["stage"],
                    "region": detail["region"],
                    "universe": detail["universe"],
                    "delay": detail["delay"],
                    "sharpe": detail["sharpe"],
                }
            )
            pyramid_to_alphas.setdefault(pyr.get("name"), []).append(
                {
                    "id": aid,
                    "status": detail["status"],
                    "sharpe": detail["sharpe"],
                    "multiplier": pyr.get("multiplier"),
                }
            )
        if (i + 1) % 25 == 0:
            log.info("  detail %d/%d", i + 1, len(all_alphas))
        time.sleep(THROTTLE)

    return attributions, pyramid_to_alphas
