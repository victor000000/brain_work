"""Recover source-language settings before selecting a refinement batch."""

import json


def python_settings(conn, candidates):
    """Read Python originals; old schemas without raw_json contain legacy rows."""
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='alpha_results' AND column_name='raw_json'"
    ).fetchone()[0]
    if not exists:
        return {}
    ids = [c[0] for c in candidates]
    rows = conn.execute(
        f"SELECT alpha_id,raw_json FROM alpha_results WHERE alpha_id IN ({','.join('?' * len(ids))})", ids
    ).fetchall()
    result = {}
    for aid, raw in rows:
        if not raw:
            continue
        body = json.loads(raw)
        settings = body.get("_submitted_settings") or body.get("settings") or {}
        if settings.get("language") == "PYTHON":
            result[aid] = settings
    return result


def preserve_python_batch(conn, cell, candidates):
    """Keep one Python source in its validated original cell and settings.

    Python's panel shapes and lookback are part of the experiment. Cross-cell
    research requires its own explicit field preflight; automatic variants
    change only the selected neutralization or decay/truncation axis.
    """
    originals = python_settings(conn, candidates)
    first = candidates[0]
    if first[0] not in originals:
        return cell, [c for c in candidates if c[0] not in originals], None
    settings = originals[first[0]]
    original_cell = tuple(first[2:5])
    if tuple(settings.get(k) for k in ("region", "universe", "delay")) != original_cell:
        raise ValueError("Python refinement has mismatched original cell")
    if type(settings.get("lookback")) is not int or not 0 <= settings["lookback"] <= 1024:
        raise ValueError("Python refinement requires original lookback")
    return original_cell, [first], dict(settings)
