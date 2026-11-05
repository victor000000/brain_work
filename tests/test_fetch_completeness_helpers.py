"""Fake session and field builder shared by the fetch-completeness tests."""


class Resp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeBrain:
    """Returns queued responses in order, recording every request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, retries=8):
        self.calls.append(params or {})
        return self.responses.pop(0)


def _field(fid, cat="pv", sub="pv-price-volume"):
    return {
        "id": fid,
        "dataset": {"id": "pv1", "name": "Price"},
        "category": {"id": cat, "name": cat},
        "subcategory": {"id": sub, "name": sub},
        "region": "USA",
        "delay": 1,
        "universe": "TOP3000",
        "type": "MATRIX",
    }
