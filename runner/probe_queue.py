"""Send finite idea probes through ordinary simulation and check machinery."""

import json
import time

import core.budget as budget
from core.log import get_file_logger
from generator.weighted_selection import record_expr_template
from runner.probe_queue_store import claim_next_probe, set_probe_state
from runner.probe_validation import validate_probe
from runner.submit_batch import submit_batch

plog = get_file_logger("submit")


def submit_queued_probe(session, conn, batch_idx, *, max_expressions=10, probe_id=None):
    """Return (handled, normal submit result), preserving the explorer contract."""
    if budget.is_exhausted():
        return True, "BUDGET"
    plan = claim_next_probe(conn, max_expressions=max_expressions, probe_id=probe_id)
    if plan is None:
        return False, None
    probe_id = plan["probe_id"]
    try:
        expressions = json.loads(plan["expressions"])
        settings = json.loads(plan["settings"])
        tags = json.loads(plan["template_tags"])
        validate_probe(conn, expressions, settings, tags)
    except (ValueError, TypeError, KeyError) as error:
        set_probe_state(conn, probe_id, "INVALID", error=str(error))
        plog.error("B%d: queued probe %s failed preflight: %s", batch_idx, probe_id[:12], error)
        return True, None

    for expression, tag in zip(expressions, tags, strict=True):
        record_expr_template(expression, tag)
    definitely_unsubmitted = False

    def rejected():
        nonlocal definitely_unsubmitted
        definitely_unsubmitted = True

    try:
        result = submit_batch(session, expressions, settings, batch_idx, conn, on_definitely_unsubmitted=rejected)
    except Exception as error:
        # A write can fail after HTTP 201. Leave the claim for parent-record
        # reconciliation on the next pass instead of blindly sending again.
        plog.error("B%d: probe %s interrupted: %s", batch_idx, probe_id[:12], error)
        raise
    if isinstance(result, dict):
        set_probe_state(conn, probe_id, "SUBMITTED", parent_id=result["pid"])
        plog.info("B%d: queued probe %s accepted as parent %s", batch_idx, probe_id[:12], result["pid"])
    elif definitely_unsubmitted:
        wait = 25 if result in ("BUDGET", "CONCURRENT") else 300
        set_probe_state(
            conn, probe_id, "PENDING", error=f"B{batch_idx}: definite rejection ({result})", retry_at=time.time() + wait
        )
    else:
        set_probe_state(conn, probe_id, "UNCERTAIN", error=f"B{batch_idx}: acceptance cannot be determined")
    return True, result
