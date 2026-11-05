"""Any-field transform templates for the BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_pick import (
    _RAW_VOLUME_EXCLUDE,
    _pick,
    _pick_group,
    _pick_price,
    _pick_return,
    _pick_tokens,
)


def winsorized_signal(fields, rng):
    """Standard cleaning pattern: backfill then winsorize.

    The pv/option catalog's `winsorized_backfilled_pattern` is this same
    expression; registering both would only double the shape's weight.
    """
    if not fields:
        return None
    field = rng.choice(fields)
    return f"winsorize(ts_backfill({field}, 63), std=4.0)"


def signed_power_transform(fields, rng):
    """Amplify extremes while preserving sign."""
    field = _pick(fields, rng, "return", "close", "volume")
    if field is None:
        return None
    power = rng.choice([0.3, 0.5, 0.7])
    return f"signed_power({field}, {power})"


def hump_turnover_controlled(fields, rng):
    """A rank signal with its day-to-day changes clipped, to spend less turnover.

    `hump(x, h)` limits the amount and magnitude of changes in its input; the
    platform states its purpose as reducing turnover, which is a submission
    check with regional ceilings (IND's is 0.4) and a term in every alpha's
    recorded `to=`. It is another of the operators with zero recorded uses
    (measured 2026-10-12): nothing in the registry spends it.

    The input is the rank of the daily return, the jumpiest shape the registry
    has. A rank crosses much of its range on a small change in the underlying
    value, so it is the shape that earns the most from being clipped —
    `ts_zscore` or a level would barely move under the same limit.

    The limit is drawn from the platform's own scale rather than invented:
    `hump`'s documented default is 0.01.

    Passed **named**, not positionally: the platform defines it as
    `hump(x, hump = 0.01)`, and the vendored grammar enforces that shape —
    `hump(x, 0.05)` fails to parse with
    `InvalidPositionalArgumentCount { expected: 1, actual: 2 }` on every render
    (caught by the registry sweep, 2026-10-12, before it cost a simulation).
    """
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    limit = rng.choice([0.01, 0.05, 0.1])
    return f"hump(rank({close} / ts_delay({close}, 1) - 1), hump={limit})"


def tvr_targeted_turnover(fields, rng):
    """Turnover set by target rather than by a fixed limit.

    `ts_target_tvr_decay(x, target_tvr=…)` does not clip the signal — it tunes
    the decay applied to it until the resulting turnover *is* the target. Where
    `hump_turnover_controlled` halves turnover with a fixed limit (measured
    2026-10-12: median 0.091 against 0.169 for the population), this asks for a
    level, which is what a regional ceiling actually is (IND's is 0.4).

    The inner signal is deliberately the same rank of the daily return the
    `hump` template uses: one base, two turnover mechanisms, so the two can be
    compared later without the signal being a confound.

    `target_tvr` is a required keyword, not the documented default —
    `ts_target_tvr_decay(close)` fails with `MissingKeyword("target_tvr")` and
    the positional form with `InvalidPositionalArgumentCount`. Both forms are
    pinned in `tests/test_operator_arity.py`, which exists because writing a
    template from the platform's own definition cost renders on every draw for
    `hump`.

    Unmeasured, and the risk to watch: the platform does the tuning internally,
    and an operator that optimizes may simulate slowly — the stale-drop path
    exists because slow cells already lose budget. If batches carrying this
    shape start appearing in STALE drops, it comes out.
    """
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    target = rng.choice([0.05, 0.1, 0.2])
    return f"ts_target_tvr_decay(rank({close} / ts_delay({close}, 1) - 1), target_tvr={target})"


def tail_extreme_signal(fields, rng):
    """Only the group-zscore tails survive; the middle of the book is zeroed.

    Straight from the forum corpus, and from the one part of it that says what
    this account needs. The post (2026-07-31) reports the numbers: expressions
    that met the RA submission standard could not be submitted because their
    prod correlation was too high, and wrapping the expression in a `tail`
    operator took PC from **0.77 to 0.68** — under the 0.7 limit — whereupon it
    submitted. The original text is one command away
    (`tools/explain_template.py 'tail('`).

    That is this account's second-largest single-check blocker
    (PROD_CORRELATION, 0.84-0.92 against 0.7, measured 2026-10-11) being moved
    by exactly the shape below. `tail` is one of the operators with zero
    recorded emissions.

    Mechanics, which is where the plausible route to that effect lives: `tail`
    returns `newval` for inputs strictly inside (lower, upper) and the input
    itself otherwise. With bounds at ±1.1 this keeps only the names a group
    z-score already calls extreme and zeroes the rest — a far sparser book than
    the ranking shapes it competes with, which is one way a candidate stops
    looking like what is already in the pool.

    The bound is drawn rather than fixed: the forum gave one value, and the
    shape is new here, so ±1.0/1.1/1.5 is a small spread around it rather than
    a commitment. `tests/test_operator_arity.py` pins the call shape — `tail`
    takes all three of `lower`, `upper`, `newval` as required keywords.
    """
    field = _pick(fields, rng, "close", "return", "volume")
    group = _pick_group(rng)
    if field is None:
        return None
    bound = rng.choice([1.0, 1.1, 1.5])
    return f"tail(group_zscore({field}, {group}), lower=-{bound}, upper={bound}, newval=0)"


def long_window_normalized(fields, rng):
    """The registry's time-series normalization at a year-long window.

    From the thread corpus's cleanest parameter finding (post 2026-09-25): one
    field family, one change — the normalization window — and the readings
    moved an order of magnitude. At window 22 the same fields read Sharpe
    1.15-1.35, under that author's submission line; at 250:

        rank(ts_zscore(Q1, 250))  S 1.700  fit 0.890  TO 30.8%  2Y 1.60  SUB 0.94  zero FAIL
        rank(ts_zscore(Q2, 250))  S 1.590  fit 0.790  TO 30.7%  2Y 1.15  SUB 1.07  zero FAIL
        ts_rank(Q1, 250)          S 1.800  fit 0.960  TO 31.5%  2Y 1.59

    The window is the finding, and it is the one part of this family the pool
    has never held: this registry's z-score shapes cap at 63 days
    (`scale_rank_zscore` draws from [10, 21, 42, 63]; `quantile_ts_rank` is a
    different normalization), while the post's are 4x longer again.

    The 2Y column is why it belongs here rather than in a notes file.
    LOW_2Y_SHARPE is this account's largest single-check blocker (742 FAIL
    sightings, values 0.41-1.17 against a 1.58 limit, measured 2026-10-11),
    and a shape whose only departure from the usual normalization is a
    year-long window is the cleanest available test of whether the window is
    what moves it.

    250 exactly as measured, not the 252 this repo usually spells a trading
    year as: the shape registered should be the shape the numbers are attached
    to.

    The field is drawn from the price, return and volume roles — each through
    its own picker, since a substring `return` match admits `return_on_equity`
    — and the shape is self-consistent whatever the operand's unit, which is
    why all three can share one template.
    """
    choices = [
        _pick(fields, rng, "close"),
        _pick_return(fields, rng),
        _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE),
    ]
    choices = [c for c in choices if c]
    if not choices:
        return None
    return f"rank(ts_zscore({rng.choice(choices)}, 250))"
