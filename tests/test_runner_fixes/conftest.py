"""Fresh in-memory DB fixture for the runner/checker/storage regression tests."""

import pytest

from core.db import connect, init_tables


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_tables(c)
    yield c
    c.close()
