"""Fakes and fixtures shared by the POST /simulations retry-policy tests.

No network and no real sleeping — the `sleeps` fixture records time.sleep.
"""

import pytest

import core.api_retry as api_retry
import core.budget as budget


class FakeResponse:
    def __init__(self, status_code, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, **kwargs):
        self.calls.append((url, json))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def clean_budget():
    """Isolate the budget singleton so one test can't exhaust another."""
    original = budget.get_state()
    budget.set_state(budget.BudgetState())
    yield
    budget.set_state(original)


@pytest.fixture
def sleeps(monkeypatch):
    recorded = []
    monkeypatch.setattr(api_retry.time, "sleep", lambda s: recorded.append(s))
    return recorded
