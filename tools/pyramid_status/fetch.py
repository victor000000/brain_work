"""BRAIN API fetchers for pyramid status snapshot."""

import time

from tools.pyramid_status._config import API_BASE, PAGE_SIZE, THROTTLE


def fetch_pyramid_multipliers(session):
    """GET current multiplier per (category, region, delay)."""
    r = session.get(f"{API_BASE}/users/self/activities/pyramid-multipliers", timeout=20)
    r.raise_for_status()
    return r.json().get("pyramids", []) or []


def fetch_alphas_by_status(session, status):
    """Paginate /users/self/alphas?status=S, return list of summary dicts."""
    out = []
    offset = 0
    while True:
        r = session.get(
            f"{API_BASE}/users/self/alphas",
            params={"status": status, "limit": PAGE_SIZE, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        j = r.json()
        results = j.get("results") or []
        if not results:
            break
        out.extend(results)
        total = j.get("count", 0) or 0
        offset += len(results)
        if offset >= total:
            break
        time.sleep(THROTTLE)
    return out


def fetch_alpha_pyramids(session, alpha_id):
    """Per-alpha detail: pyramids + pyramidThemes + sharpe.

    Returns None on non-200, else a dict with the fields we use downstream.
    """
    r = session.get(f"{API_BASE}/alphas/{alpha_id}", timeout=20)
    if r.status_code != 200:
        return None
    j = r.json() or {}
    pyramids = j.get("pyramids") or []
    is_block = j.get("is") or {}
    sharpe = is_block.get("sharpe") if isinstance(is_block, dict) else None
    settings = j.get("settings") or {}
    return {
        "pyramids": pyramids,
        "stage": j.get("stage"),
        "status": j.get("status"),
        "region": settings.get("region"),
        "universe": settings.get("universe"),
        "delay": settings.get("delay"),
        "sharpe": sharpe,
    }
