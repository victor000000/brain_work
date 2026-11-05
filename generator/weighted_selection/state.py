"""UsageState singleton + DB-backed operator-usage cache + expression bookkeeping."""

import json
import math
import os
import time

from core.log import get_file_logger
from core.log_config import LOG_DIR

glog = get_file_logger("generator")

# How long a load_usage result is considered fresh enough to skip re-reading
# from SQLite. The explorer calls generate_expressions on every batch, which
# previously meant a full operator_usage scan per batch — wasted work, since
# the explorer also reloads in periodic_maintenance.
USAGE_TTL_SECONDS = 60

# Upper bound on the expression -> template-name map. `_release` and
# `lookup_expr_template` drop entries that are known dead (a combo's halves, an
# expression that failed validation), but they are an optimisation rather than
# the bound: `storage/track_templates` peeks instead of consuming, so an entry
# nobody releases lives until FIFO eviction.
#
# 2,000 was under half a day of generation, and that bound — not just restarts
# — is why ~1.2% of stored alphas carry no shape label: an alpha is stored when
# its simulation finishes, minutes and thousands of expressions after its
# draw, so the entry can be evicted *before* the store that needs it. Raised to
# two days' worth and, more importantly, backed by the ledger below, which is
# what actually survives a restart.
MAX_TRACKED_EXPRESSIONS = 20000
_ENCODED_EXPR_PREFIX = "@json:"


def _ledger_path():
    """Path of the durable attribution ledger (env override wins).

    One `name\texpr` line per recorded draw, keyed like the map. Multiline
    expressions are tagged JSON strings so each draw stays on one line; a failed
    append is dropped (`record_expr_template` must never break a batch) and
    `load_ledger` ignores a missing or unreadable file.
    """
    override = os.environ.get("BRAIN_EXPR_TEMPLATE_PATH")
    if override:
        return override
    return os.path.join(LOG_DIR, ".expr_templates.tsv")


def _append_ledger(expr, name):
    if any(char in expr for char in "\t\r\n") or expr.startswith(_ENCODED_EXPR_PREFIX):
        expr = _ENCODED_EXPR_PREFIX + json.dumps(expr, ensure_ascii=True)
    try:
        with open(_ledger_path(), "a", encoding="utf-8") as fh:
            fh.write(f"{name}\t{expr}\n")
    except OSError as e:
        glog.debug("template ledger append failed: %s", e)


# The ledger is append-only and nothing prunes it: ~0.6 MB/day at the current
# draw rate (measured 2026-10-13: 16 KB in the first five hours, most of it
# from a parked explorer's maintenance draws). That is deliberate for now.
# Compaction from a process that may not be the only writer has a race with no
# cheap fix — the read-the-tail-then-replace pattern drops any append landing
# between the read and the `os.replace`, because the appender's open handle
# still points at the replaced inode. `load_ledger` bounds what is *in memory*;
# bounding the *file* wants a single-writer design (the explorer compacting at
# startup, with the tools' appends excluded while it does), not a rewrite here.


# How stale an in-memory view of the ledger may be before a lookup re-reads
# it. The first read is unconditional; later ones cost a file tail read, so the
# TTL bounds that to once a minute from a hot loop.
LEDGER_RELOAD_SEC = 60


def load_ledger(ttl_seconds=None):
    """Fold the ledger's tail into the map.

    The first call of a state always reads. Later calls re-read only when
    `ttl_seconds` is given and that much time has passed — the first version
    read exactly once, which turned out to be the wrong shape: a slotless
    constant like `(close - vwap) / vwap` is recorded, then *popped* by
    `_release` when a 4-field build uses it as a half, and the alpha arrives
    minutes later to a map that no longer holds it and a reader that would not
    look again. Nine alphas in the first two hours of 2026-10-14 were labelled
    `unknown` that way, all of them constants from `vwap_close_spread` and its
    siblings — the durable record had them the whole time.
    """
    now = time.time()
    if getattr(_state, "ledger_loaded", False):
        last = getattr(_state, "ledger_loaded_at", 0.0)
        if ttl_seconds is None or (now - last) < ttl_seconds:
            return
    _state.ledger_loaded = True
    _state.ledger_loaded_at = now
    try:
        with open(_ledger_path(), encoding="utf-8") as fh:
            lines = fh.readlines()[-MAX_TRACKED_EXPRESSIONS:]
    except OSError:
        return
    entries = _state.expr_templates
    for line in lines:
        name, _, expr = line.rstrip("\n").partition("\t")
        if expr.startswith(_ENCODED_EXPR_PREFIX):
            try:
                expr = json.loads(expr[len(_ENCODED_EXPR_PREFIX) :])
            except ValueError:
                continue
            if not isinstance(expr, str):
                continue
        if expr:
            entries[expr] = name


class UsageState:
    """Holds operator usage counts + a transient expression->template-name map."""

    def __init__(self):
        self.usage_cache: dict[str, int] = {}
        self.expr_templates: dict[str, str] = {}
        # Wall-clock timestamp of the most recent successful load_usage().
        self.loaded_at: float = 0.0
        # False until `load_ledger` has folded the persisted tail in;
        # `ledger_loaded_at` is when, for the reload TTL.
        self.ledger_loaded: bool = False
        self.ledger_loaded_at: float = 0.0

    def reset(self):
        self.usage_cache = {}
        self.expr_templates = {}
        self.loaded_at = 0.0
        self.ledger_loaded = False
        self.ledger_loaded_at = 0.0


_state = UsageState()


def get_state() -> UsageState:
    return _state


def set_state(state: UsageState) -> None:
    global _state
    _state = state


def record_expr_template(expr, name):
    """Record which template generated an expression (FIFO-capped)."""
    if expr is None:
        return
    entries = _state.expr_templates
    entries[expr] = name
    while len(entries) > MAX_TRACKED_EXPRESSIONS:
        del entries[next(iter(entries))]
    _append_ledger(expr, name)


def lookup_expr_template(expr):
    """Look up and consume the template name recorded for an expression."""
    load_ledger()
    return _state.expr_templates.pop(expr, None)


def peek_expr_template(expr):
    """The template name recorded for an expression, without consuming it.

    `storage.track_templates` reads this rather than `lookup_expr_template`,
    because the map is keyed by the expression *string* and a slotless template
    emits the same string on every draw: `(close - vwap) / vwap` is
    `vwap_close_spread` whatever the cell or the field pool. A consuming read
    attributes the first alpha of that shape and leaves every later one to the
    regex fallback, which has no pattern for a pure-arithmetic expression — so
    they were recorded as `unknown`, and `unknown` is a name nothing weights.

    Measured 2026-10-08: 8-12% of each day's alphas were `unknown`, and the
    sample is dominated by exactly those constants (`(close - vwap) / vwap`,
    `(high - low) / close`). The two templates they come from were the day's
    largest built-in producers, so their measured yield was being split across
    a template name and a hole. `MAX_TRACKED_EXPRESSIONS` bounds the map, so
    not consuming costs a bounded amount of memory and buys the attribution.

    The durable ledger is folded in first, so an expression drawn before a
    restart — or evicted before its simulation finished — still resolves. That
    is the 1.2% of stored alphas (2,841 rows, measured 2026-10-13) this read
    used to lose to the legacy signature list or to `unknown`.
    """
    load_ledger(ttl_seconds=LEDGER_RELOAD_SEC)
    return _state.expr_templates.get(expr)


def load_usage(conn, force=False):
    """Load operator usage from DB into the cache (TTL-cached).

    Returns the cached values if they were loaded less than USAGE_TTL_SECONDS
    ago. Pass force=True from the explorer's periodic_maintenance to ensure
    a refresh on the documented cadence (every CHECK_INTERVAL completions).
    """
    if not force and _state.usage_cache and (time.time() - _state.loaded_at) < USAGE_TTL_SECONDS:
        return
    new_cache: dict[str, int] = {}
    try:
        for op, cnt in conn.execute("SELECT operator, SUM(count) FROM operator_usage GROUP BY operator").fetchall():
            new_cache[op] = cnt
    except Exception as e:
        glog.warning("Failed to load operator usage: %s", e)
        return
    _state.usage_cache = new_cache
    _state.loaded_at = time.time()
    glog.debug("Loaded usage for %d operators", len(_state.usage_cache))


def get_weight(operators):
    """Weight = 1 / (1 + log1p(min usage among operators)).

    Logarithmic, not linear. The linear form has an unbounded range and the
    usage counts are large — `rank` alone sits at 155,700 — so `1/(1+usage)`
    put **21 of the registry's 38 templates below 1e-4** and handed 95.6% of
    the weight to the two whose operators happened to be least used (measured
    2026-10-07: `vwap_close_spread` and `high_low_spread`, 47.8% each, and
    they were indeed the day's two biggest built-in producers).

    Among the unselectable were the four templates with the best correlation
    record in the account's history — `ts_backfill_negmean`, `staleness_decay`,
    `scale_rank_zscore`, `power_ratio`, zero correlation failures across 495
    checked alphas — which had produced **no alphas at all since 2026-10-03**.

    log1p keeps the ordering, so the exploration pressure survives: a template
    built from rare operators still outweighs one built from ubiquitous ones,
    by ~13x at the extremes rather than ~400,000x. No template becomes
    unreachable.
    """
    if not operators:
        return 1.0
    min_usage = min(_state.usage_cache.get(op, 0) for op in operators)
    return 1.0 / (1.0 + math.log1p(min_usage))
