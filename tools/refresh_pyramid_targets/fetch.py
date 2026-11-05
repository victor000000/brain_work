"""BRAIN API fetchers for pyramid alpha counts + multipliers."""

from tools.refresh_pyramid_targets._config import API_BASE


def fetch_pyramid_alphas(session, start, end):
    """GET /pyramid-alphas with optional date window. Returns the pyramids list."""
    params = {}
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end
    r = session.get(
        f"{API_BASE}/users/self/activities/pyramid-alphas",
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("pyramids", []) or []


def fetch_pyramid_multipliers(session):
    """GET current multipliers per (category, region, delay)."""
    r = session.get(f"{API_BASE}/users/self/activities/pyramid-multipliers", timeout=30)
    r.raise_for_status()
    return r.json().get("pyramids", []) or []
