"""Small builders shared by the runner/checker/storage regression tests."""

import time

from runner.explore_loop.constants import STALE_TIMEOUT
from storage.store_sim import store_sim


class FakeResponse:
    """Minimal requests.Response stand-in for fake sessions."""

    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.headers = dict(headers or {})
        self.content = b"{}" if json_data is not None else b""
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


def batch_settings(region="USA", universe="TOP3000", delay=1, **over):
    settings = {
        "region": region,
        "universe": universe,
        "delay": delay,
        "neutralization": "MARKET",
        "decay": 4,
        "truncation": 0.08,
    }
    settings.update(over)
    return settings


def batch_info(pid="P1", idx=1, exprs=("rank(x)",), settings=None, **extra):
    info = {
        "pid": pid,
        "loc": f"https://api.worldquantbrain.com/simulations/{pid}",
        "idx": idx,
        "exprs": list(exprs),
        "settings": batch_settings(**(settings or {})),
        "submitted_at": time.time(),
    }
    info.update(extra)
    return info


def stale_batch(pid="P1"):
    """A batch that has been sitting past STALE_TIMEOUT."""
    info = batch_info(pid=pid)
    info["submitted_at"] = time.time() - STALE_TIMEOUT - 10
    return info


def parent_row(conn, pid="P1"):
    """Store the SUBMITTED parent row the poll loop expects for `pid`."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    store_sim(conn, pid, None, 1, "rank(x)", "USA", "TOP3000", 1, "SUBMITTED", None, None, batch_settings(), ts)
