"""Execute or poll the frozen PV portfolio diagnostic; never start broad search."""

import argparse
import fcntl
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict

from core import budget
from core.auth import get_session
from core.db import get_conn
from core.log_config import LOG_DIR
from runner import super_probe

PLAN = Path("brain_logs/superalpha_pv_baseline_preflight_20261025.json")
PLAN_SHA = "764449093c015f8ad548626a0be2d22c9c35901721907a472b30c3d90b0359ad"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--execute", action="store_true")
    action.add_argument("--poll", metavar="OWNER")
    action.add_argument("--fetch-result", metavar="OWNER")
    args = parser.parse_args()
    with (Path(LOG_DIR) / "explorer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = PLAN.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PLAN_SHA:
            raise ValueError("Frozen plan changed")
        session = get_session(raise_on_failure=True)
        # Explicitly disable transport retries for this mutation path.
        session.mount("https://", HTTPAdapter(max_retries=0))
        conn = get_conn()
        try:
            super_probe.initialize(conn)
            if args.execute:
                owner = super_probe.enqueue(conn, json.loads(raw))
                row = super_probe.dispatch(conn, owner, session, budget.is_exhausted)
            elif args.poll:
                owner = args.poll
                row = super_probe.poll(conn, owner, session)
            else:
                owner = args.fetch_result
                row = super_probe.fetch_result(conn, owner, session)
            evidence = json.loads(row["evidence"])
            if args.execute and evidence:
                budget.update_from_headers(CaseInsensitiveDict(evidence[-1].get("headers", {})))
            target = Path(LOG_DIR) / f"super_probe_{owner}.json"
            target.write_text(json.dumps({"owner": owner, **row}, indent=2))
            print(
                json.dumps(
                    {
                        "owner": owner,
                        "state": row["state"],
                        "receipt": row["receipt"],
                        "next_poll": row["next_poll"],
                        "artifact": str(target),
                    }
                )
            )
        finally:
            conn.close()


if __name__ == "__main__":
    main()
