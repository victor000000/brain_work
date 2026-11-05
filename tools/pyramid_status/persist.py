"""DB upserts + JSON snapshot dump for pyramid_status."""

import json

from core.db import connect
from tools.pyramid_status._config import DB_PATH, RESULT_PATH
from tools.pyramid_status._log import log
from tools.pyramid_status.schema import ensure_schema


def persist_to_db(multipliers, attributions, fetched_at):
    """Insert multiplier snapshot + upsert attribution rows."""
    conn = connect(DB_PATH)
    ensure_schema(conn)

    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO pyramid_multipliers "
            "(category, region, delay, multiplier, fetched_at) VALUES (?, ?, ?, ?, ?)",
            [
                ((m.get("category") or {}).get("id"), m.get("region"), m.get("delay"), m.get("multiplier"), fetched_at)
                for m in multipliers
            ],
        )
        if attributions:
            conn.executemany(
                "INSERT OR REPLACE INTO pyramid_alpha_attribution "
                "(alpha_id, pyramid_name, multiplier, status, stage, region, universe, "
                " delay, sharpe, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        r["alpha_id"],
                        r["pyramid_name"],
                        r["multiplier"],
                        r["status"],
                        r["stage"],
                        r["region"],
                        r["universe"],
                        r["delay"],
                        r["sharpe"],
                        fetched_at,
                    )
                    for r in attributions
                ],
            )
    conn.close()
    log.info("Persisted: %d multipliers, %d attribution rows", len(multipliers), len(attributions))


def dump_json(multipliers, alphas_by_status, attributions, fetched_at):
    """Write the full snapshot to RESULT_PATH for downstream tooling."""
    with open(RESULT_PATH, "w") as f:
        json.dump(
            {
                "fetched_at": fetched_at,
                "multipliers": multipliers,
                "alphas_by_status": {st: [a.get("id") for a in xs] for st, xs in alphas_by_status.items()},
                "attributions": attributions,
            },
            f,
            indent=2,
            sort_keys=True,
        )
    log.info("Wrote %s", RESULT_PATH)
