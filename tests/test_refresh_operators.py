"""The operator refresh keeps the allowlist equal to the platform's list.

`generator/validate.py` refuses any call not in the `operators` table, so an
operator the platform added after the last import is unreachable: the generator
cannot emit it, and a mined skeleton that uses it fails `is_usable`. Nothing
fetched `/operators` before 2026-10-11, which is how the table came to hold 83
operators against the platform's 84.
"""

import sys

import pytest

from core.db import connect
from tools import refresh_operators


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Returns a canned operator list and records that it was asked once."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        return FakeResponse(self.payload)


@pytest.fixture
def conn(monkeypatch):
    """An in-memory operators table holding what the last import left."""
    c = connect(":memory:")
    c.execute(refresh_operators.DDL)
    c.execute(
        refresh_operators.INSERT,
        ("rank", "Cross Sectional", "ALL", "rank(x)", "Ranks.", '["REGULAR"]', "{}"),
    )
    c.commit()
    return c


def _run(monkeypatch, conn, session, argv=()):
    monkeypatch.setattr(sys, "argv", ["refresh_operators", *argv])
    return refresh_operators.main(conn=conn, session=session)


def test_adds_an_operator_the_platform_has_and_we_do_not(monkeypatch, conn):
    """`vector_neut` is the operator this was written for, found live 2026-10-11."""
    session = FakeSession(
        [
            {"name": "rank", "category": "Cross Sectional", "definition": "rank(x)"},
            {
                "name": "vector_neut",
                "category": "Cross Sectional",
                "level": "ALL",
                "definition": "vector_neut(x, y)",
                "description": "Neutralizes against a vector field.",
                "scope": ["REGULAR"],
            },
        ]
    )
    assert _run(monkeypatch, conn, session) == 0
    names = {row[0] for row in conn.execute("SELECT name FROM operators").fetchall()}
    assert names == {"rank", "vector_neut"}
    # The whole payload is kept, because the operator's parameter list is what
    # the fill-time type check reads when a template calls it.
    raw = conn.execute("SELECT raw_json FROM operators WHERE name='vector_neut'").fetchone()[0]
    assert "vector_neut(x, y)" in raw


def test_removes_an_operator_the_platform_no_longer_lists(monkeypatch, conn):
    """Keeping it would let the generator emit a call the platform rejects."""
    conn.execute(
        refresh_operators.INSERT,
        ("retired_op", "Arithmetic", "ALL", "retired_op(x)", "", None, "{}"),
    )
    conn.commit()
    session = FakeSession([{"name": "rank", "category": "Cross Sectional", "definition": "rank(x)"}])
    assert _run(monkeypatch, conn, session) == 0
    names = {row[0] for row in conn.execute("SELECT name FROM operators").fetchall()}
    assert names == {"rank"}


def test_dry_run_reports_and_writes_nothing(monkeypatch, conn):
    session = FakeSession([{"name": "vector_neut", "definition": "vector_neut(x, y)"}])
    assert _run(monkeypatch, conn, session, argv=["--dry-run"]) == 0
    names = {row[0] for row in conn.execute("SELECT name FROM operators").fetchall()}
    assert names == {"rank"}, "the dry run must not add rows"
