"""Single-attempt SUPER requests. Caller must hold the explorer writer lock.

Persist the claim before transport; even a crash before sending leaves an owner
that cannot be replayed. Raw native evidence is retained separately from any
interpretation of portfolio performance or selected component membership.
"""

import hashlib
import json
import math
import re
import time
from urllib.parse import urljoin, urlparse

BASE = "https://api.worldquantbrain.com"


def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS super_probe_requests (
        owner VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL, plan VARCHAR NOT NULL,
        state VARCHAR NOT NULL, receipt VARCHAR, evidence VARCHAR NOT NULL,
        next_poll DOUBLE NOT NULL, updated DOUBLE NOT NULL)""")
    conn.commit()


def enqueue(conn, plan):
    payload = plan["payload"]
    if payload.get("type") != "SUPER" or not payload.get("selection") or not payload.get("combo"):
        raise ValueError("Expected explicit SUPER selection and combo")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    owner = hashlib.sha256(encoded.encode()).hexdigest()
    conn.execute(
        "INSERT OR IGNORE INTO super_probe_requests VALUES (?, ?, ?, 'READY', NULL, '[]', 0, ?)",
        (owner, encoded, json.dumps(plan), time.time()),
    )
    conn.commit()
    return owner


def read(conn, owner):
    row = conn.execute(
        "SELECT payload, plan, state, receipt, evidence, next_poll, updated FROM super_probe_requests WHERE owner=?",
        (owner,),
    ).fetchone()
    if row is None:
        raise ValueError("Unknown owner")
    return dict(zip(("payload", "plan", "state", "receipt", "evidence", "next_poll", "updated"), row, strict=False))


def save(conn, owner, state, evidence, receipt=None, next_poll=0):
    conn.execute(
        "UPDATE super_probe_requests SET state=?, evidence=?, receipt=?, next_poll=?, updated=? WHERE owner=?",
        (state, json.dumps(evidence), receipt, next_poll, time.time(), owner),
    )
    conn.commit()


def snapshot(response):
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text[:16000]}
    return {
        "at": time.time(),
        "http": response.status_code,
        "headers": {
            k: v
            for k, v in response.headers.items()
            if k.lower()
            in {"location", "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"}
        },
        "body": body,
    }


def receipt_url(value):
    if not value:
        return None
    url = urljoin(BASE, value)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.worldquantbrain.com":
        return None
    if not parsed.path.startswith("/simulations/") or parsed.query or parsed.fragment:
        return None
    return url


def dispatch(conn, owner, session, exhausted):
    row = read(conn, owner)
    if row["state"] != "READY":
        raise ValueError("Owner already claimed; never replay")
    if exhausted():
        raise ValueError("Native allowance exhausted")
    evidence = json.loads(row["evidence"])
    save(conn, owner, "CLAIMED", evidence)
    try:
        response = session.post(
            BASE + "/simulations", json=json.loads(row["payload"]), timeout=60, allow_redirects=False
        )
    except Exception as exc:
        evidence.append({"at": time.time(), "transport_error": type(exc).__name__})
        save(conn, owner, "UNCERTAIN", evidence)
        return read(conn, owner)
    evidence.append(snapshot(response))
    receipt = receipt_url(response.headers.get("Location")) if response.status_code == 201 else None
    state = "SUBMITTED" if receipt else "UNCERTAIN"
    if 400 <= response.status_code < 500:
        state = "REJECTED"
    save(conn, owner, state, evidence, receipt, time.time() + 30)
    return read(conn, owner)


def poll(conn, owner, session):
    row = read(conn, owner)
    if row["state"] != "SUBMITTED" or not receipt_url(row["receipt"]):
        raise ValueError("No pending receipted owner")
    if time.time() < row["next_poll"]:
        return row
    response = session.get(row["receipt"], timeout=60, allow_redirects=False)
    item = snapshot(response)
    evidence = [*json.loads(row["evidence"]), item]
    body = item["body"]
    state = "SUBMITTED"
    if response.status_code == 200 and isinstance(body, dict):
        if body.get("status") in {"ERROR", "FAIL", "CANCELLED"}:
            state = "FAILED"
        elif body.get("alpha"):
            # Receipt completion is distinct from identity/membership verification.
            state = "RESULT_READY"
    try:
        delay = float(response.headers.get("Retry-After", 30))
        if not math.isfinite(delay):
            delay = 60
    except (TypeError, ValueError):
        delay = 60
    save(conn, owner, state, evidence, row["receipt"], time.time() + max(30, delay))
    return read(conn, owner)


def fetch_result(conn, owner, session):
    """Retain the native alpha and compare exact submitted settings and code.

    VERIFIED_IDENTITY does not verify membership, OS performance or acceptance.
    Failed GETs retain RESULT_READY so only the safe GET may be repeated.
    """
    row = read(conn, owner)
    if row["state"] != "RESULT_READY":
        raise ValueError("Owner has no result ready to retrieve")
    evidence = json.loads(row["evidence"])
    receipt = next(e for e in reversed(evidence) if e.get("body", {}).get("alpha"))
    alpha_id = receipt["body"]["alpha"]
    if not isinstance(alpha_id, str) or not re.fullmatch(r"[A-Za-z0-9]+", alpha_id):
        raise ValueError("Invalid native alpha ID")
    response = session.get(BASE + "/alphas/" + alpha_id, timeout=60, allow_redirects=False)
    item = snapshot(response)
    item["resource"] = "alpha"
    evidence.append(item)
    state = "RESULT_READY"
    if response.status_code == 200:
        native = item["body"]
        payload = json.loads(row["payload"])
        differences = {}
        for key in ("selection", "combo"):
            returned = native.get(key)
            code = returned.get("code") if isinstance(returned, dict) else returned
            if code != payload[key]:
                differences[key] = {"expected": payload[key], "actual": code}
        for key, value in payload["settings"].items():
            if native.get("settings", {}).get(key) != value:
                differences["settings." + key] = {"expected": value, "actual": native.get("settings", {}).get(key)}
        if native.get("id") != alpha_id or native.get("type") != "SUPER":
            differences["identity"] = {"id": native.get("id"), "type": native.get("type")}
        item["identity_differences"] = differences
        state = "IDENTITY_MISMATCH" if differences else "VERIFIED_IDENTITY"
    save(conn, owner, state, evidence, row["receipt"])
    return read(conn, owner)
