"""Parent-row builder shared by the children/expression-mismatch tests."""

import json
import time

from storage.store_sim import store_sim
from tests.test_runner_fixes.helpers import batch_settings


def parent(conn, pid="P1", exprs=("a", "b")):
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    store_sim(
        conn,
        pid,
        None,
        1,
        json.dumps(list(exprs)),
        "USA",
        "TOP3000",
        1,
        "SUBMITTED",
        None,
        None,
        batch_settings(),
        ts,
    )
