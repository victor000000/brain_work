"""Shared fixture and session builder for the poll_batch regression tests."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from storage.store_sim import store_sim
from tests.test_runner_fixes.helpers import batch_settings


@pytest.fixture(autouse=True)
def stored_parent(conn):
    """The poll loop only ever sees batches whose parent row was stored on 201."""
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    store_sim(conn, "P1", None, 1, "rank(x)", "USA", "TOP3000", 1, "SUBMITTED", None, None, batch_settings(), ts)


def session_for(resp):
    session = MagicMock()
    session.get.return_value = resp
    return session
