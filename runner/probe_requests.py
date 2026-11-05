"""Immutable plan requests consumed by the explorer's existing DuckDB writer."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from core.log import get_file_logger
from core.log_config import LOG_DIR
from runner.probe_queue_store import enqueue_probe, utc_now
from runner.probe_validation import validate_probe

log = get_file_logger("submit")
MAX_PLAN_BYTES = 2 * 1024 * 1024
MAX_PLAN_BATCHES = 64
MAX_REQUESTS_PER_PASS = 4


def _directory(inbox):
    return Path(inbox) if inbox is not None else Path(LOG_DIR) / "probe_requests"


def _batches(raw):
    if len(raw) > MAX_PLAN_BYTES:
        raise ValueError("probe request exceeds 2 MiB")
    document = json.loads(raw)
    batches = document.get("batches") if isinstance(document, dict) else None
    if not isinstance(batches, list) or not 1 <= len(batches) <= MAX_PLAN_BATCHES:
        raise ValueError("probe request requires 1 to 64 batches")
    if any(not isinstance(batch, dict) for batch in batches):
        raise ValueError("probe batches must be objects")
    return batches


def _atomic_write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _receipt_path(request):
    return request.with_name(request.name.removesuffix(".plan.json") + ".receipt.json")


def request_probe_plan(plan_path, inbox=None):
    """Publish a frozen request without opening DuckDB or contacting BRAIN.

    This is a request, not proof of enqueueing. The writer's APPLIED receipt
    supplies the queue IDs; native acceptance is still a separate event.
    """
    path = Path(plan_path)
    if path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("probe request exceeds 2 MiB")
    raw = path.read_bytes()
    _batches(raw)
    digest = hashlib.sha256(raw).hexdigest()
    request = _directory(inbox) / f"{digest}.plan.json"
    if request.exists():
        if request.is_symlink() or request.read_bytes() != raw:
            raise ValueError("existing request does not match its digest")
    else:
        _atomic_write(request, raw)
    return {
        "requested": True,
        "plan_sha256": digest,
        "request_path": str(request),
        "receipt_path": str(_receipt_path(request)),
    }


def _already_processed(receipt, digest):
    try:
        document = json.loads(receipt.read_text())
        return document.get("plan_sha256") == digest and document.get("state") in ("APPLIED", "REJECTED")
    except (OSError, ValueError, AttributeError):
        return False


def _process_request(conn, path, digest):
    """Validate the entire plan before inserting any batch; replay is idempotent."""
    try:
        if path.is_symlink() or path.stat().st_size > MAX_PLAN_BYTES:
            raise ValueError("unsafe or oversized probe request")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("probe request digest mismatch")
        batches = _batches(raw)
        for batch in batches:
            validate_probe(conn, batch["expressions"], batch["settings"], batch["template_tags"])
    except (ValueError, TypeError, KeyError) as error:
        return {"state": "REJECTED", "plan_sha256": digest, "at_utc": utc_now(), "error": str(error)}
    queue = [
        dict(
            zip(
                ("probe_id", "inserted"),
                enqueue_probe(conn, b["expressions"], b["settings"], b["template_tags"]),
                strict=True,
            )
        )
        for b in batches
    ]
    return {
        "state": "APPLIED",
        "applied": True,
        "plan_sha256": digest,
        "at_utc": utc_now(),
        "expressions": sum(len(batch["expressions"]) for batch in batches),
        "queue": queue,
    }


def ingest_probe_requests(conn, inbox=None):
    """Called only by the explorer; never submits, polls, or resets a probe.

    A crash after an insert or before receipt publication leaves the immutable
    request for replay. enqueue_probe preserves already claimed/accepted states.
    Transient errors retain the request rather than falsely rejecting it.
    """
    directory = _directory(inbox)
    if not directory.exists():
        return []
    outcomes = []
    attempted = 0
    for path in sorted(directory.glob("*.plan.json")):
        digest = path.name.removesuffix(".plan.json")
        receipt = _receipt_path(path)
        if _already_processed(receipt, digest):
            continue
        if attempted >= MAX_REQUESTS_PER_PASS:
            break
        attempted += 1
        try:
            outcome = _process_request(conn, path, digest)
            _atomic_write(receipt, (json.dumps(outcome, indent=2) + "\n").encode())
        except Exception as error:
            log.warning("Probe request %s retained for reconciliation: %s", digest[:12], error)
            continue
        outcomes.append(outcome)
        log.info("Probe request %s %s", digest[:12], outcome["state"])
    return outcomes
