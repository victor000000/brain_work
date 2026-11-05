"""The portable test command must not open live data or a network socket."""

import os
import socket
from pathlib import Path

import duckdb
import pytest
from pytest_socket import SocketBlockedError

pytestmark = pytest.mark.skipif(os.environ.get("BRAIN_TEST_OFFLINE") != "1", reason="offline command contract")


def test_project_database_is_blocked_at_the_raw_driver():
    path = Path(__file__).resolve().parents[1] / "brain_data.duckdb"
    with pytest.raises(RuntimeError, match="cannot open the project database"):
        duckdb.connect(str(path))


def test_synthetic_database_remains_usable(tmp_path):
    conn = duckdb.connect(str(tmp_path / "fixture.duckdb"))
    try:
        assert conn.execute("SELECT 42").fetchone() == (42,)
    finally:
        conn.close()


def test_network_sockets_are_blocked():
    with pytest.raises(SocketBlockedError):
        socket.socket()
