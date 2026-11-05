"""Parent-row builders shared by the startup re-attach tests."""

import json
import time

from storage.store_sim import store_sim
from tests.test_runner_fixes.helpers import batch_settings


def ts(now):
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))


def parent(conn, pid, idx, timestamp, exprs=("rank(x)",), status="SUBMITTED"):
    store_sim(
        conn,
        pid,
        None,
        idx,
        json.dumps(list(exprs)),
        "USA",
        "TOP3000",
        1,
        status,
        None,
        None,
        batch_settings(),
        timestamp,
    )
