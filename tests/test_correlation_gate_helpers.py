"""Fake session/response doubles shared by the correlation-gate tests."""

import json


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, content=b"{}"):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        if json_data is None:
            self.content = b""
        else:
            self.content = json.dumps(json_data).encode()

    def json(self):
        return self._json


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return self.responses.pop(0)


SELF_URL = "/alphas/A1/correlations/self"
