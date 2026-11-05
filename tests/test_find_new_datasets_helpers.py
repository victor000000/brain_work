"""Fakes and fixtures shared by the find_new_datasets scan tests."""

import pytest

from tools.find_new_datasets import scan as scan_mod


class Resp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class FakeBrain:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, retries=8):
        self.calls.append(params)
        return self.responses.pop(0)


def field(did, cat="pv"):
    return {"id": f"f_{did}", "dataset": {"id": did, "name": did}, "category": {"id": cat}}


@pytest.fixture
def one_combo(monkeypatch):
    """Restrict REGION_CONFIG to a single combo so call counts are exact."""
    monkeypatch.setattr(scan_mod, "REGION_CONFIG", {"USA": {"universes": ["TOP3000"], "delays": [1]}})
