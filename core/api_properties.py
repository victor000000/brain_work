"""BRAIN API — alpha property endpoints. PATCH /alphas/{id} (description)."""

from core.api import API
from core.log import get_file_logger

alog = get_file_logger("alpha")


def patch_alpha_description(session, alpha_id, description):
    """Set alpha description via PATCH. Required for submission."""
    try:
        resp = session.patch(
            f"{API}/alphas/{alpha_id}",
            json={"regular": {"description": description}},
        )
        alog.debug("Patch desc %s: HTTP %d", alpha_id, resp.status_code)
        return resp.status_code == 200
    except Exception as e:
        alog.warning("Patch desc %s failed: %s", alpha_id, e)
        return False
