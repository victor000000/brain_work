"""Rounds of drawing, validating and deduplicating a generation batch.

Split out of `generator/random_generator.py`, which calls `collect_valid` with
its own `batch` closure; the closure stays there because it resolves the
built-in builders through that module's globals (tests patch them there).
"""

import collections

from core.log import get_file_logger
from generator.template_fill import filled_expression_problem
from generator.weighted_selection import lookup_expr_template

glog = get_file_logger("generator")

# Extra generation passes allowed when validation drops candidates. The built-in
# path is not self-validating, so a template bug can waste the whole batch; the
# retries give the generator a chance to fill the batch from its other paths.
GENERATION_ROUNDS = 3

# Expressions emitted recently, across batches. `seen` below covers one call
# only, so a skeleton with no `{f}` slot emits the *same string* every draw —
# `(close - vwap) / vwap` was simulated 19 times today — and a filled one
# recurs whenever the same field lands in the same slot. Measured 2026-10-07:
# 232 of ~1,700 fresh alphas were exact duplicates of an earlier one, ~14% of
# the budget spent re-simulating a signal we already have.
_RECENT_LIMIT = 2000
_recent: collections.deque[str] = collections.deque(maxlen=_RECENT_LIMIT)
_recent_set: set[str] = set()


def _remember(expr: str) -> None:
    if len(_recent) == _RECENT_LIMIT:
        _recent_set.discard(_recent[0])
    _recent.append(expr)
    _recent_set.add(expr)


def collect_valid(batch, pools, count: int, stats: dict, region, universe, delay) -> list[str]:
    """Draw, validate and dedupe up to `count` expressions for one cell.

    `batch(n, allow_templates)` returns raw candidates; `pools` is
    `(field_pool, known_operators, vector_fields, group_fields)`, the same
    contract the mined-pool path applies at fill time.

    A round that produces nothing sets `allow_templates` False for the rest of
    the passes, so a broken template path cannot starve the batch.
    """
    field_pool, known_operators, vector_fields, group_fields = pools
    result: list[str] = []
    seen: set[str] = set()
    dropped = 0
    allow_templates = True
    for round_idx in range(GENERATION_ROUNDS):
        if len(result) >= count:
            break
        # The last pass accepts a recently-seen expression rather than
        # under-filling the batch: a small cell whose whole reachable space is
        # already in `_recent` would otherwise shrink every batch until it could
        # not be submitted at all.
        last_round = round_idx == GENERATION_ROUNDS - 1
        before = len(result)
        for expr in batch(count - len(result), allow_templates):
            if expr in seen or (not last_round and expr in _recent_set):
                # A duplicate is discarded and its tracking entry is left alone.
                # The map is keyed by the expression *string*, so a slotless
                # template emitting a constant (`(close - vwap) / vwap`) records
                # the same key on every draw, and the earlier copies are still
                # awaiting storage — `_recent` holds 2000 expressions and
                # storage lags generation by a whole simulation. Releasing here
                # evicted the attribution those copies still needed, and the
                # regex fallback has no pattern for a pure-arithmetic
                # expression, so they landed in `template_performance` as
                # `unknown` — the name nothing weights. Measured 2026-10-08:
                # 8-12% of every day's alphas, dominated by exactly those
                # constants. `MAX_TRACKED_EXPRESSIONS` is what bounds the map.
                #
                # An invalid expression is still released below: validation is
                # deterministic, so a string that fails now failed then too.
                continue
            seen.add(expr)
            # Same contract the mined-pool path applies at fill time: syntax,
            # operator allowlist, field membership, and the MATRIX/VECTOR/GROUP
            # type of every operator argument. The built-ins used to get the
            # syntax check alone, so a template that put a datafield where a
            # `group_*` operator wants a grouping reached the platform and came
            # back `Incompatible unit ... expected "Unit[Group:1]"` — a
            # simulation spent for nothing (observed live 2026-10-06).
            problem = filled_expression_problem(expr, field_pool, known_operators, vector_fields, group_fields)
            if problem is not None:
                dropped += 1
                glog.warning("Dropped invalid generated expression (%s): %s", problem, expr[:120])
                lookup_expr_template(expr)
                continue
            result.append(expr)
            _remember(expr)
        if len(result) == before:
            # Nothing survived validation this round — stop spending it on the
            # template path and let the built-ins fill the rest.
            allow_templates = False

    if dropped:
        glog.warning("Dropped %d invalid expression(s) for %s/%s/d%d", dropped, region, universe, delay)
    glog.info("Generated %d/%d for %s/%s/d%d (%d errors)", len(result), count, region, universe, delay, stats["errors"])
    return result
