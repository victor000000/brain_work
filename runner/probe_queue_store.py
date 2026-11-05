"""Durable probe payloads and reconciliation with 201-accepted parents."""

import hashlib
import json
import time

from runner.probe_validation import validate_probe
from runner.python_probe_source import python_source_identity


def utc_now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def enqueue_probe(conn, expressions, settings, template_tags):
    """Validate and insert once; identical payloads never reset a spent probe."""
    validate_probe(conn, expressions, settings, template_tags)
    identities = (
        [python_source_identity(expr) for expr in expressions] if settings.get("language") == "PYTHON" else expressions
    )
    payload = [sorted(identities), settings]
    probe_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    inserted = conn.execute(
        "INSERT OR IGNORE INTO probe_batches (probe_id, expressions, settings, template_tags, created_at) "
        "VALUES (?, ?, ?, ?, ?) RETURNING probe_id",
        (probe_id, json.dumps(expressions), json.dumps(settings), json.dumps(template_tags), utc_now()),
    ).fetchall()
    conn.commit()
    return probe_id, bool(inserted)


def set_probe_state(conn, probe_id, state, *, parent_id=None, error=None, retry_at=0):
    conn.execute(
        "UPDATE probe_batches SET state=?, parent_id=?, error_message=?, retry_at=? WHERE probe_id=?",
        (state, parent_id, error, retry_at, probe_id),
    )
    conn.commit()


def reconcile_claimed_probes(conn):
    """Recover an accepted-but-unacknowledged batch; never re-POST ambiguity.

    Parent records are written only after HTTP 201. A crash after that write
    must not duplicate the probe; a crash with no parent cannot prove the POST
    was unsent, so it is held for inspection rather than retried automatically.
    """
    claimed = conn.execute(
        "SELECT probe_id, expressions, settings, claimed_at FROM probe_batches WHERE state='CLAIMED'"
    ).fetchall()
    for probe_id, expressions, settings, claimed_at in claimed:
        try:
            expected_expressions, expected_settings = json.loads(expressions), json.loads(settings)
            cell = [expected_settings[name] for name in ("region", "universe", "delay")]
        except (TypeError, ValueError, KeyError):
            set_probe_state(conn, probe_id, "UNCERTAIN", error="interrupted claim has an unreadable payload")
            continue
        parents = conn.execute(
            "SELECT sim_id, expression, raw_settings FROM simulations "
            "WHERE parent_id IS NULL AND submitted_at >= ? AND region=? AND universe=? AND delay=?",
            (claimed_at, *cell),
        ).fetchall()
        matches = []
        for sim_id, raw_expressions, raw_settings in parents:
            try:
                actual = json.loads(raw_expressions)
                actual = [actual] if isinstance(actual, str) else actual
                if actual == expected_expressions and json.loads(raw_settings) == expected_settings:
                    matches.append(sim_id)
            except (TypeError, ValueError):
                continue
        if matches:
            set_probe_state(conn, probe_id, "SUBMITTED", parent_id=matches[0])
        else:
            set_probe_state(conn, probe_id, "UNCERTAIN", error="interrupted claim without a stored acceptance")


def claim_next_probe(conn, max_expressions=10, *, probe_id=None):
    """Reserve a ready batch, prioritizing untouched work over elapsed retries.

    The loop's concurrent-limit sleep can exceed a rejected probe's delay.
    Sorting only by creation time would then retry that same probe every pass,
    leaving all later requests untouched. Fresh work has retry_at=0; once all
    fresh requests have had a turn, due retries run in due-time order.
    An old schema simply has no probes.
    A supplied probe_id restricts selection to that exact owner; it never
    falls through to another ready probe when the owner is ineligible.
    """
    exists = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='probe_batches'").fetchone()
    if not exists or exists[0] != 1:
        return None
    reconcile_claimed_probes(conn)
    row = conn.execute(
        "SELECT probe_id, expressions, settings, template_tags FROM probe_batches "
        "WHERE state='PENDING' AND retry_at<=? AND (? IS NULL OR probe_id=?) "
        "AND COALESCE(json_array_length(TRY_CAST(expressions AS JSON)),0)<=? "
        "ORDER BY retry_at, created_at, probe_id LIMIT 1",
        (time.time(), probe_id, probe_id, max_expressions),
    ).fetchone()
    if row is None:
        return None
    probe_id, expressions, settings, tags = row
    updated = conn.execute(
        "UPDATE probe_batches SET state='CLAIMED', claimed_at=? "
        "WHERE probe_id=? AND state='PENDING' RETURNING probe_id",
        (utc_now(), probe_id),
    ).fetchall()
    conn.commit()
    if not updated:
        return None
    return {"probe_id": probe_id, "expressions": expressions, "settings": settings, "template_tags": tags}
