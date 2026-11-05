"""Shared helpers and fixtures for the pyramid_storage test package."""

from unittest.mock import MagicMock

import requests

from core.db import connect, init_tables


def mem_conn():
    """In-memory DB with WAL-style PRAGMAs matching production."""
    conn = connect(":memory:")
    init_tables(conn)
    return conn


# Shared API-shaped responses used by the fetch and store/refresh tests.
PYRAMID_MULT_RESPONSE = {
    "pyramids": [
        {"category": {"id": "pv", "name": "Price Volume"}, "region": "USA", "delay": 0, "multiplier": 1.6},
        {"category": {"id": "fundamental", "name": "Fundamental"}, "region": "USA", "delay": 1, "multiplier": 1.4},
        {"category": {"id": "sentiment", "name": "Sentiment"}, "region": "CHN", "delay": 0, "multiplier": 1.9},
    ]
}

PYRAMID_ALPHAS_RESPONSE = {
    "pyramids": [
        {"category": {"id": "pv", "name": "Price Volume"}, "region": "USA", "delay": 0, "alphaCount": 12},
        {"category": {"id": "fundamental", "name": "Fundamental"}, "region": "USA", "delay": 1, "alphaCount": 0},
        {"category": {"id": "sentiment", "name": "Sentiment"}, "region": "CHN", "delay": 0, "alphaCount": 0},
    ]
}


def mock_session(get_responses):
    """Build a MagicMock session whose .get(url) returns responses in order.

    `get_responses` is a list of (status_code, payload) tuples where:
    - If `payload` is a BaseException instance, session.get() itself raises
      that exception — this models a *transport-level* failure (connection
      error, timeout, etc.).  The status_code is ignored in this case and can
      be None or 0.
    - If `payload` is a dict (or list) and status_code >= 400, the mock
      returns a Response whose raise_for_status() raises requests.HTTPError —
      this models a real HTTP error response (e.g. a 500 from the server).
    """
    session = MagicMock()
    call_iter = iter(get_responses)

    def side_effect(*_args, **_kwargs):
        status, payload = next(call_iter)
        if isinstance(payload, BaseException):
            raise payload
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = payload
        resp.raise_for_status = MagicMock()
        if status >= 400:
            resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
        return resp

    session.get.side_effect = side_effect
    return session
