"""Fetch pyramid-multipliers + pyramid-alpha-counts from BRAIN."""

import requests

from core.log import get_file_logger

API_BASE = "https://api.worldquantbrain.com"
plog = get_file_logger("pyramid")


def fetch_pyramid_state(session):
    """Fetch (multipliers, alpha_counts) from BRAIN, projecting JSON to flat dicts.

    Returns:
        (multipliers, alpha_counts) where each is a list of flat dicts on
        success, or (None, None) on any HTTP/JSON failure. Never raises on
        HTTP/JSON failure (a malformed-but-200 response with missing keys will
        still surface a KeyError — intentional signal that the API shape changed).
    """
    try:
        m_resp = session.get(f"{API_BASE}/users/self/activities/pyramid-multipliers", timeout=15)
        m_resp.raise_for_status()
        m_payload = m_resp.json()
        a_resp = session.get(f"{API_BASE}/users/self/activities/pyramid-alphas", timeout=15)
        a_resp.raise_for_status()
        a_payload = a_resp.json()
    except (requests.RequestException, ValueError) as e:
        plog.warning("fetch_pyramid_state failed: %s", e)
        return None, None

    multipliers = [
        {
            "category": p["category"]["id"],
            "region": p["region"],
            "delay": p["delay"],
            "multiplier": p["multiplier"],
        }
        for p in m_payload.get("pyramids", [])
    ]
    alpha_counts = [
        {
            "category": p["category"]["id"],
            "region": p["region"],
            "delay": p["delay"],
            "alpha_count": p["alphaCount"],
        }
        for p in a_payload.get("pyramids", [])
    ]
    return multipliers, alpha_counts
