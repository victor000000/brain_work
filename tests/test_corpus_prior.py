"""Measured-yield weights for the mined template corpora."""

import pytest

from generator import corpus_prior as cp
from generator.template_source_pick import _corpus_row_weights


class _Conn:
    """Minimal stand-in for the compat connection: one canned result set."""

    def __init__(self, rows, raises=None):
        self._rows = rows
        self._raises = raises

    def execute(self, sql, params=()):
        if self._raises:
            raise self._raises
        return _Cursor(self._rows)


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.fixture(autouse=True)
def _clean_prior(monkeypatch):
    """Every test starts from a cleared prior and the default env."""
    monkeypatch.delenv("BRAIN_CORPUS_PRIOR", raising=False)
    cp._multipliers.clear()
    cp._measured.clear()
    yield
    cp._multipliers.clear()
    cp._measured.clear()


def _rows(forum=(2380, 6), proven=(98, 2)):
    return [("pool:forum", forum[0], forum[1]), ("pool:proven", proven[0], proven[1])]


def test_an_unloaded_prior_leaves_the_size_weighting_alone():
    """Before the first load — and after a load that could not read — nothing moves."""
    pool = [{"corpus": "forum"}] * 4 + [{"corpus": "proven"}]
    assert sum(_corpus_row_weights(pool)) == pytest.approx(2 + 1)


def test_the_better_corpus_gets_the_larger_multiplier():
    """The measured gap: `proven` 2/98 against `forum` 6/2,380."""
    cp.load_corpus_prior(_Conn(_rows()))
    assert cp.corpus_multiplier("proven") > 1.0
    assert cp.corpus_multiplier("forum") < 1.0
    assert cp.measured("proven") == (98, 2)


def test_the_multiplier_lifts_the_corpus_share():
    """The weights are per row, so the corpus' total share is `n * weight`."""
    pool = [{"corpus": "forum"}] * 4 + [{"corpus": "proven"}] * 2
    before_forum = sum(w for w, t in zip(_corpus_row_weights(pool), pool, strict=True) if t["corpus"] == "forum")
    cp.load_corpus_prior(_Conn(_rows()))
    after_forum = sum(w for w, t in zip(_corpus_row_weights(pool), pool, strict=True) if t["corpus"] == "forum")
    assert after_forum < before_forum


def test_a_corpus_with_no_outcomes_is_not_penalised():
    """Unmeasured is not bad: a corpus absent from the window keeps 1.0."""
    cp.load_corpus_prior(_Conn(_rows()))
    assert cp.corpus_multiplier("helpcenter") == 1.0
    assert cp.corpus_multiplier("cnhkmcp") == 1.0


def test_a_thin_corpus_barely_moves():
    """Shrinkage: 16 alphas with no hits must not buy a punitive multiplier."""
    cp.load_corpus_prior(_Conn([*_rows(), ("pool:helpcenter", 16, 0)]))
    assert cp.corpus_multiplier("helpcenter") > cp.MIN_MULTIPLIER
    assert cp.corpus_multiplier("helpcenter") < 1.0


def test_the_multiplier_is_clamped():
    """A perfect record on a small sample cannot take the pool outright."""
    cp.load_corpus_prior(_Conn([("pool:forum", 5000, 0), ("pool:proven", 300, 300)]))
    assert cp.corpus_multiplier("proven") <= cp.MAX_MULTIPLIER
    assert cp.corpus_multiplier("forum") >= cp.MIN_MULTIPLIER


def test_no_hits_anywhere_is_a_tie():
    """With nothing at the floor every rate shrinks to the same value."""
    cp.load_corpus_prior(_Conn([("pool:forum", 5000, 0), ("pool:proven", 98, 0)]))
    assert cp.corpus_multiplier("forum") == pytest.approx(1.0)
    assert cp.corpus_multiplier("proven") == pytest.approx(1.0)


def test_an_empty_window_changes_nothing():
    cp.load_corpus_prior(_Conn([]))
    assert cp.corpus_multiplier("forum") == 1.0


def test_a_broken_read_stays_out_of_the_way():
    """A prior is an optimisation; a query that cannot run must not stop a batch."""
    cp.load_corpus_prior(_Conn(None, raises=RuntimeError("no such table")))
    assert cp.corpus_multiplier("forum") == 1.0


def test_the_env_switch_disables_it(monkeypatch):
    monkeypatch.setenv("BRAIN_CORPUS_PRIOR", "0")
    cp.load_corpus_prior(_Conn(_rows()))
    assert cp.corpus_multiplier("proven") == 1.0
