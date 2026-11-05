"""fetch_pyramid_state — happy path + transport / partial / 5xx failures."""

import requests

from tests.test_pyramid_storage.conftest import (
    PYRAMID_ALPHAS_RESPONSE,
    PYRAMID_MULT_RESPONSE,
    mock_session,
)


def test_fetch_pyramid_state_happy_path():
    """Fetch projects API JSON to flat dicts: category.id flattened, alphaCount renamed."""
    from download.pyramid import fetch_pyramid_state

    session = mock_session(
        [
            (200, PYRAMID_MULT_RESPONSE),
            (200, PYRAMID_ALPHAS_RESPONSE),
        ]
    )
    multipliers, alpha_counts = fetch_pyramid_state(session)

    assert multipliers == [
        {"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6},
        {"category": "fundamental", "region": "USA", "delay": 1, "multiplier": 1.4},
        {"category": "sentiment", "region": "CHN", "delay": 0, "multiplier": 1.9},
    ]
    assert alpha_counts == [
        {"category": "pv", "region": "USA", "delay": 0, "alpha_count": 12},
        {"category": "fundamental", "region": "USA", "delay": 1, "alpha_count": 0},
        {"category": "sentiment", "region": "CHN", "delay": 0, "alpha_count": 0},
    ]


def test_fetch_pyramid_state_transport_error_returns_none_pair():
    """Transport-level failure on first GET returns (None, None) without raising."""
    from download.pyramid import fetch_pyramid_state

    session = mock_session([(None, requests.RequestException("boom"))])
    assert fetch_pyramid_state(session) == (None, None)


def test_fetch_pyramid_state_partial_failure_returns_none_pair():
    """First GET ok, second GET fails (transport) -> (None, None), no half-snapshot."""
    from download.pyramid import fetch_pyramid_state

    session = mock_session(
        [
            (200, PYRAMID_MULT_RESPONSE),
            (None, requests.RequestException("alphas endpoint down")),
        ]
    )
    assert fetch_pyramid_state(session) == (None, None)


def test_fetch_pyramid_state_5xx_response_returns_none_pair():
    """HTTP 5xx response on first GET (raise_for_status path) returns (None, None)."""
    from download.pyramid import fetch_pyramid_state

    session = mock_session([(500, {"error": "internal"})])
    assert fetch_pyramid_state(session) == (None, None)
