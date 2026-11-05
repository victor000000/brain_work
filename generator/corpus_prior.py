"""Per-corpus draw weights for the mined-template pool, fitted on outcomes.

`template_source_pick._corpus_row_weights` gives each corpus a share going as
the square root of its usable size — diminishing returns to size, so a small
corpus is not drowned by a large one. That term models *how much text* a corpus
contributed and says nothing about whether its shapes work, and the two
corpora that dominate the pool differ on exactly that by an order of magnitude.

Measured over 2026-10-07..10-10, share of a corpus' alphas reaching the 1.58
sharpe floor:

| corpus | alphas | at the floor | rate |
|---|---|---|---|
| built-ins (reference) | 12,764 | 269 | **2.11%** |
| `pool:proven` | 98 | 2 | **2.04%** |
| `pool:forum` | 2,380 | 6 | **0.25%** |

`proven` yields like the built-ins and `forum` yields eight times worse, while
the size term hands `forum` 66% of the pool's draws against `proven`'s 21%.
Restricted to the two days since the corpus was rebuilt (10-09..10-10) the gap
is wider still — 2 of 98 against 1 of 576.

So the weight gains a measured term: `sqrt(n) * (shrunk rate / pool rate)`.
The rate is shrunk toward the pool mean with an additive prior, which is what
keeps a 98-alpha sample from buying a 12x multiplier outright, and it is
clamped, so no corpus can be voted off the pool. A corpus with no rows in the
window keeps a multiplier of exactly 1.0 — it is unmeasured, not bad.

**What this does not claim.** `proven`'s shapes were chosen because the
platform accepted alphas of that shape, so its record is partly retrospective;
2 hits is a small sample and the shrinkage is doing real work. The window is
30 days and refits every batch, so if the gap is noise it closes on its own
within days rather than needing a revert. Set `BRAIN_CORPUS_PRIOR=0` to take
the prior out entirely and restore the pure size weighting.

The rate this fits is the *sharpe* floor, which is measured at simulation
time, and it is the only per-corpus outcome that exists — **no `pool:` alpha
has ever reached a correlation check** (every checked alpha in
`submission_checks` is a built-in), so the one cost this concentrates is the
one with no evidence about it. The direction of that risk is worth stating:
`proven`'s shapes are the account's own accepted shapes, so more of them could
mean more SELF_CORRELATION against what is already submitted. It is bounded by
the clamp and by `proven` being ~5% of generation at the resulting share, and
it is the next thing to measure once pool alphas start reaching checks.

`forum`'s share falls from 66% to ~40% under this, which is the intended
trade — its alphas reach the floor at 0.21% — but it is also the corpus the
Makefile keeps a standing share for, as the only source of community shapes to
be *uncorrelated* with. It keeps 40% of the pool, not zero.
"""

import os

from core.log import get_file_logger
from core.time_sql import utc_timestamp_sql

glog = get_file_logger("generator")

# Outcomes behind each corpus' rate are read from this window. Recency matters
# for the same reason it does in `sign_policy`: a corpus is re-mined, and the
# record that should weight it is the one for the shapes it holds now.
WINDOW_DAYS = 30

# Additive prior strength, in units of "pseudo-alphas at the pool mean". With
# 200, a corpus needs ~200 alphas before its own rate outweighs the pool's —
# `forum` (2,380) is past it, `proven` (98) is not, `helpcenter` (16) is far
# short. Raising it flattens the multipliers toward 1.0.
SHRINK_ALPHAS = 200.0

# Bounds on the multiplier itself. The floor keeps a corpus in the pool at a
# usable share even after a bad window (an uncorrelated source that never
# yields is still worth its traffic — correlation, not sharpe, is the binding
# submission gate and `forum` is the only community-shaped source); the cap
# keeps one corpus from taking the pool on a small sample.
MIN_MULTIPLIER = 0.25
MAX_MULTIPLIER = 4.0

# The prefix `template_source_pick` records a pool alpha under.
_PREFIX = "pool:"

# corpus -> multiplier. Empty means "no evidence for any corpus", in which case
# every lookup returns 1.0 and the pool weights exactly as it did before.
_multipliers: dict[str, float] = {}
_measured: dict[str, tuple[int, int]] = {}


def _window_start(days: int) -> str:
    """UTC date `days` back, compared with normalized platform instants."""
    import datetime

    return (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")


def _enabled() -> bool:
    return os.environ.get("BRAIN_CORPUS_PRIOR", "1") not in ("0", "", "false", "False")


def load_corpus_prior(conn) -> None:
    """Refit the per-corpus multipliers from stored outcomes.

    Never raises: a corpus prior is an optimisation, and a database that cannot
    answer (a fresh schema, a locked file) must leave generation weighting
    exactly as it was rather than stop a batch.
    """
    global _multipliers, _measured
    _multipliers, _measured = {}, {}
    if not _enabled():
        return
    try:
        rows = conn.execute(
            "SELECT template, COUNT(*), "
            "  SUM(CASE WHEN is_sharpe >= 1.58 THEN 1 ELSE 0 END) "
            "FROM alpha_results "
            f"WHERE template LIKE ? AND {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP) "
            "GROUP BY template",
            (_PREFIX + "%", _window_start(WINDOW_DAYS)),
        ).fetchall()
    except Exception as e:
        glog.warning("corpus prior: could not read outcomes (%s); using size weights", e)
        return

    counts = {str(t)[len(_PREFIX) :]: (int(n), int(h)) for t, n, h in rows if t}
    total_n = sum(n for n, _h in counts.values())
    total_h = sum(h for _n, h in counts.values())
    if total_n <= 0:
        return
    pool_rate = total_h / total_n

    for corpus, (n, hits) in counts.items():
        # Shrink the corpus' own rate toward the pool's, then express it as a
        # multiplier on the pool rate. `pool_rate > 0` is guaranteed by the
        # `total_h` term of the prior: with no hits anywhere every rate shrinks
        # to the same value and every multiplier is 1.0.
        rate = (hits + SHRINK_ALPHAS * pool_rate) / (n + SHRINK_ALPHAS)
        mult = rate / pool_rate if pool_rate > 0 else 1.0
        _multipliers[corpus] = max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, mult))
        _measured[corpus] = (n, hits)

    glog.info(
        "corpus prior: %s",
        ", ".join(f"{c} x{_multipliers[c]:.2f} ({_measured[c][1]}/{_measured[c][0]})" for c in sorted(_multipliers)),
    )


def corpus_multiplier(corpus) -> float:
    """Multiplier for one corpus' pool weight; 1.0 when unmeasured."""
    return _multipliers.get(corpus, 1.0)


def measured(corpus):
    """`(alphas, hits)` behind a corpus' multiplier, or None if unmeasured."""
    return _measured.get(corpus)
