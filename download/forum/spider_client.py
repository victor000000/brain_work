"""One `ForumClient` per worker thread for the spider's thread pools.

Split out of `download/forum/spider.py`, which re-exports `_client` and calls
it from `harvest_bodies`.
"""

from __future__ import annotations

import threading

from download.forum.client import ForumClient

_local = threading.local()


def _client() -> ForumClient:
    """One session per worker thread — requests.Session is not thread-safe."""
    client = getattr(_local, "client", None)
    if client is None:
        client = ForumClient()
        _local.client = client
    return client
