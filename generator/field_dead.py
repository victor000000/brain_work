"""Fields the platform has never once simulated into an alpha.

Distinct from the *description* filters in `field_queries` (a label, a status
code, an identifier — categories that are not measurements whatever the data
says). This one is purely empirical: a field is dead when our own recorded
simulations show it has been drawn and **never produced an alpha**, because the
platform refuses it or its data is missing in that cell.

Measured 2026-10-11 over 44,764 children since 2026-10-01, against cell alpha
rates of 79-100% outside AMR:

| pool | fields | child sims | alphas |
|---|---|---|---|
| `pv20_returns*_t_*` (the `_t_` variant family) | 43 | 151 | **0** |
| every other field in the pool | ~6,100 | 112,187 | 99,580 (88.8%) |

At an 88% base rate, 151 draws with no alpha is not luck. The same record holds
for the AMR-only `pv20_returns*` fields individually (10 draws, 0 alphas each).
And the cost is not the draw: a ten-expression batch is all-or-nothing, so one
dead expression spends ten simulations — the amplification measured in
TODO.md's AMR item. In AMR, 9.3% of children touched a field this module
excludes, which predicts 62% of ten-batches failing against 61% measured.

**Why it is scored on two levels.** Per field alone the `_t_` family is
invisible: 43 fields share 151 draws, about 3.5 each. Pooled by family — the id
with its trailing `_<digits>` removed — the record is decisive. Both levels
require **zero** alphas, and the family bar is higher (10 draws against 3),
because pooling weaker evidence needs a stronger prior.

**It self-heals, which is the point of the window.** The record is the last
`WINDOW_DAYS` only. A field the rule excludes stops being drawn, so its evidence
ages out after the window and it returns to the pool, where a fresh draw either
produces an alpha or refreshes the evidence. A field excluded on a bad fortnight
is not excluded forever, and a field that starts working comes back on its own.
"""

import re
import time

from core.log import get_file_logger

flog = get_file_logger("fields")

WINDOW_DAYS = 14
# Per field: a handful of draws with no alpha is already implausible where the
# cell's rate is 80%+, and three is the fewest that is not a coin flip.
MIN_USES = 3
# Per family: pooling 43 fields' thin records into one needs more than that.
MIN_FAMILY_USES = 10

_TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_DIGIT_RUN = re.compile(r"\d+")

_cache: tuple[float, set[str]] = (0.0, set())
CACHE_SEC = 1800


def family_of(field_id: str) -> str:
    """The id with every digit run masked — the pooling key.

    `pv20_returns4_t_1663`, `pv20_returns10_t_1660` and `pv20_returns750_t_631`
    all key to `pv20_returns#_t_#`, which is what makes the `_t_` variant family
    visible: 43 fields sharing 151 draws, about 3.5 each, is nothing per field
    and decisive pooled.

    Only the part after the dataset prefix is masked, so `pv20_close_9` and
    `pv37_close_9` stay in different families — the dataset number identifies
    which data a field reads, and pooling across it would let one dataset's
    record speak for another's. A family qualifies only when **none** of its members
    has produced an alpha, so one working sibling keeps the whole family in the
    pool — which is also why a coarse key is safe.
    """
    head, sep, tail = field_id.partition("_")
    return head + sep + _DIGIT_RUN.sub("#", tail)


def dead_fields(conn, now=None, window_days=WINDOW_DAYS):
    """Field ids to keep out of the series pools, from recorded outcomes.

    Returns an empty set — never raises — when the query cannot run: a database
    that cannot answer must leave generation exactly as it was rather than stop
    a batch, the same contract `load_prior` and `load_corpus_prior` keep.
    """
    since = time.strftime("%Y-%m-%d", time.gmtime((now or time.time()) - window_days * 86400))
    try:
        rows = conn.execute(
            """
            SELECT alpha_id, expression FROM simulations
            WHERE parent_id IS NOT NULL AND completed_at >= ? AND expression IS NOT NULL
            """,
            (since,),
        ).fetchall()
    except Exception as e:  # a schema without `simulations`, or a locked file
        flog.debug("dead-field scan unavailable: %s", e)
        return set()

    vocab = _field_vocab(conn)
    uses: dict[str, int] = {}
    alphas: dict[str, int] = {}
    family_uses: dict[str, int] = {}
    family_alphas: dict[str, int] = {}
    for alpha_id, expression in rows:
        hit = {t for t in _TOKEN.findall(expression) if t in vocab}
        for f in hit:
            uses[f] = uses.get(f, 0) + 1
            fam = family_of(f)
            family_uses[fam] = family_uses.get(fam, 0) + 1
            if alpha_id:
                alphas[f] = alphas.get(f, 0) + 1
                family_alphas[fam] = family_alphas.get(fam, 0) + 1

    dead = {f for f, n in uses.items() if n >= MIN_USES and not alphas.get(f)}
    dead |= {f for f in uses if family_uses[family_of(f)] >= MIN_FAMILY_USES and not family_alphas.get(family_of(f))}
    if dead:
        flog.info(
            "dead fields: excluding %d of %d drawn (window %dd, %d children scanned)",
            len(dead),
            len(uses),
            window_days,
            len(rows),
        )
    return dead


def _field_vocab(conn) -> set[str]:
    try:
        return {row[0] for row in conn.execute("SELECT DISTINCT id FROM data_fields").fetchall() if row[0]}
    except Exception:
        return set()


def cached_dead_fields(conn, now=None):
    """`dead_fields` behind a process cache, for the per-batch pool loaders.

    The scan reads every child simulation in the window; the loaders run once
    per batch, so recomputing it each time would cost seconds a batch for an
    answer that moves only when new results land.
    """
    global _cache
    stamp, value = _cache
    clock = now or time.time()
    if clock - stamp < CACHE_SEC:
        return value
    value = dead_fields(conn, now=clock)
    _cache = (clock, value)
    return value


def reset_cache():
    """Drop the cache (tests, or after a bulk re-import of results)."""
    global _cache
    _cache = (0.0, set())
