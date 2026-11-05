"""Preserve the platform's confirmed submission date alongside alpha data."""

import json

from core.log import get_file_logger

clog = get_file_logger("check")


def store_submission_receipt(conn, alpha_id, submitted, platform_status):
    """Merge verified GET evidence without replacing metrics or local status.

    Persistence failure cannot undo the platform's confirmed acceptance. Log
    the missing receipt, but leave the caller's verified outcome intact.
    """
    patch = {"dateSubmitted": submitted}
    if platform_status is not None:
        patch["status"] = platform_status
    try:
        with conn:
            row = conn.execute(
                "UPDATE alpha_results SET raw_json=json_merge_patch(COALESCE(NULLIF(raw_json,''),'{}'), ?) "
                "WHERE alpha_id=? RETURNING alpha_id",
                (json.dumps(patch), alpha_id),
            ).fetchone()
        if row is None:
            clog.warning("Verified submission %s has no local alpha record for its receipt", alpha_id)
            return False
        return True
    except Exception as error:
        clog.warning("Could not persist verified submission receipt for %s: %s", alpha_id, error)
        return False
