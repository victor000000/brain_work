"""Re-simulate near-miss alphas under different simulation settings.

An alpha that fails exactly one submission check has already cleared 13-14 of
them: its *idea* is sound and the cell is legal, so a settings change — which
alters the simulated PnL, and with it the correlation and long-horizon checks —
has a far better chance of producing a submittable alpha than a fresh random
expression does. Measured 2026-10-05: of ~2,700 generated alphas, 5 passed the
local gate and none passed every check, while three sat on a single failure
(`KPrnJYa1` LOW_2Y_SHARPE 1.37 vs 1.58; `A1vnNpoR` and `e7QnxeZJ`
IS_LADDER_SHARPE).

So the explore loop spends `POLISH_RATE` of its batches on these instead of new
alphas. A polish batch holds the candidates of *one* cell (settings are
per-batch, not per-expression) under a neutralization the alpha has not been
simulated with — repeating the original settings would reproduce the original
failure.

The queue is filled by `storage.store_checks` and drained here; `attempts`
bounds the spend per candidate so one stubborn near-miss cannot absorb the
budget.

The queue scan itself lives in `runner.explore_helpers.polish_queue` and the
pass-weight query in `runner.explore_helpers.polish_weights`; both are
re-exported here so `from runner.explore_helpers.polish import ...` keeps
working for callers and tests.
"""

import math
import random

from runner.explore_helpers.polish_queue import take_batch  # noqa: F401
from runner.explore_helpers.polish_weights import outcome_weights  # noqa: F401
from runner.setting_pools import DECAYS, TRUNCATIONS
from runner.settings_factory import ALLOWED_NEUT_BY_REGION, pick_neutralization

# The truncation axis the queue varies — deliberately dipping below the
# generation pool's 0.05 floor.
#
# The corpus holds a DEU/TOP500 field report on exactly this check
# (`docs/forum/forum_bodies.json`, post 42627500535575): truncation's
# semantics is the *max single-stock weight share*, 5-8% never binds
# because the cap is never reached, and 0.01-0.02 is the zone that
# turned CONCENTRATED_WEIGHT to PASS — "candidate families judged dead
# revived overnight". The axis is kept because it costs nothing to carry
# and may move other classes; but the claim itself failed its first live
# test (2026-10-16): the same expression at t=0.02/d15 against its
# t=0.1/d8 original read CONCENTRATED_WEIGHT 0.234203 against 0.233743 —
# unmoved to the third decimal, and the class is excluded in
# `store_checks_polish.NON_CONVERTING_CHECKS` again. The generation pool bottoms at 0.05, so the
# settings axis had never tested the working zone at all; the polish
# queue is where a candidate-specific repair belongs, and the flat
# sharpe across 0.05/0.08/0.1 in the stored population (floor rate
# 2.0%/1.7%/2.1%, n~24k) says the generation pool itself has nothing to
# gain from moving yet.
_POLISH_TRUNCATIONS = tuple(sorted(set(TRUNCATIONS) | {0.01, 0.02}))

# One batch in POLISH_EVERY re-runs near-misses.
#
# Measured 2026-10-05, which is why this is aggressive: of 42 alphas the polish
# path produced, 3 were accepted by the platform (7.1%) and 19 reached the
# submission sharpe floor (45%). Of 3,571 freshly generated alphas, none were
# accepted and ~0.5% reached the floor. A polish alpha is worth ~15x a fresh one
# per simulation spent, and it costs less budget too (3 expressions per batch
# against 10).
#
# It is also self-limiting, so the tilt cannot run away: candidates retire after
# POLISH_MAX_ATTEMPTS, new ones only arrive when a check finds an alpha one
# failure short, and an empty queue returns None and falls straight through to
# normal generation. Exploration therefore continues at whatever rate the
# near-miss supply can support.
#
# Deterministic on `batch_idx` rather than a coin flip: a ~15% chance per batch
# is unverifiable from the outside (29 batches with no fire is unlikely but
# indistinguishable from a broken gate), and when the queue is short it wastes
# draws on batches that cannot use them anyway.
POLISH_EVERY = 2
# Candidates per polish batch (settings are shared, so they must share a cell).
POLISH_MAX_EXPRS = 3
# Re-runs per candidate before it is left alone.
POLISH_MAX_ATTEMPTS = 4

_rng = random.Random()


def should_polish(batch_idx) -> bool:
    """True when this batch should re-run a near-miss instead of generating."""
    return batch_idx % POLISH_EVERY == 0


# Which axis a polish batch varies, on every other polish batch. Measured
# 2026-10-11 on the 99 expressions that have two or more checked alphas: 16 have
# one alpha passing every check and another failing one, and on distinct
# expressions **9 converted on decay/truncation alone against 8 on
# neutralization alone**. `take_batch` only ever varied the neutralization, so
# half of those conversions were unreachable. Half the batches keep the old axis
# so the two are directly comparable afterwards.
POLISH_SETTINGS_EVERY = 2

# `tried` entries for the settings axis, tagged so they cannot be mistaken for
# a neutralization name (the column held bare names before this).
_SET_TAG = "SET"


def _settings_pair_key(decay, truncation):
    """Match configured decimals after a DuckDB REAL/float32 round trip."""
    value = float(truncation)
    for preset in _POLISH_TRUNCATIONS:
        if math.isclose(value, preset, rel_tol=1e-7, abs_tol=1e-10):
            value = preset
            break
    return f"{decay}:{value}"


def variant_settings(rng=None, tried=(), originals=()):
    """A `(decay, truncation)` pair this candidate has not been simulated under.

    Must differ from *every* original in the batch — settings are shared across
    a batch's candidates, so a pair matching any one of them would re-run that
    candidate's identical simulation, which is what `tried` exists to prevent.
    Returns None when no pair qualifies, and the caller keeps the old axis.
    """
    rng = rng or _rng
    seen = {entry.split(":", 1)[1] for entry in tried if str(entry).startswith(_SET_TAG + ":")}
    seen |= {_settings_pair_key(d, t) for d, t in originals}
    options = [(d, t) for d in sorted(set(DECAYS)) for t in _POLISH_TRUNCATIONS if f"{d}:{t}" not in seen]
    return rng.choice(options) if options else None


def format_settings_tried(decay, truncation) -> str:
    """The `tried` entry recording a settings variant."""
    return f"{_SET_TAG}:{decay}:{truncation}"


def tries_neutralization(entry: str) -> bool:
    """True when a `tried` entry names a neutralization rather than a setting.

    The column is shared by both axes and predates the tag, so a bare name is a
    neutralization and anything tagged is not.
    """
    return not str(entry).startswith(_SET_TAG + ":")


def variant_neutralization(region, original, rng=None, weights=None, tried=()):
    """A region-legal neutralization other than `original`, or None if none is.

    Repeating the original would re-run the same alpha; the point is to change
    the risk model the PnL is neutralized against. `weights` (see
    `outcome_weights`) biases the choice toward neutralizations the platform has
    passed before; without it the pick is uniform.

    `tried` holds neutralizations this candidate has already been polished
    under. Excluding only `original` was not enough: a candidate re-run under
    one it had already been simulated with is an *identical* simulation, since
    the expression and cell are unchanged. Measured 2026-10-06/07: 50 such
    repeats in a day, up to four times for a single candidate.
    """
    rng = rng or _rng
    allowed = ALLOWED_NEUT_BY_REGION.get(region)
    if not allowed:
        # Unknown region: fail closed to the picker's own restricted set.
        picked = pick_neutralization(region)
        return None if picked == original or picked in tried else picked
    others = sorted(set(allowed) - {original} - set(tried))
    if not others:
        return None
    if not weights:
        return rng.choice(others)
    return rng.choices(others, weights=[weights.get(n, 0.5) for n in others], k=1)[0]
