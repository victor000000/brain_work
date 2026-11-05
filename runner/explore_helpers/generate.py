"""generate_and_submit — pyramid3-targeted batch generation and submission."""

import random

import core.budget as budget
from core.regions import REGION_CONFIGS
from generator.diversity_picker import pyramid3_weighted_pick
from generator.field_picker_matrix import set_target_category
from generator.interface import generate
from runner.explore_helpers import polish
from runner.explore_helpers._constants import BATCH_SIZE, elog
from runner.explore_helpers.polish_claim import release_unsubmitted_claim
from runner.probe_queue import submit_queued_probe
from runner.settings_factory import make_settings, pick_neutralization
from runner.submit_batch import submit_batch

_rng = random.Random()


def _generate_with_target(
    conn, region, delay, universe, neutralization, target_category, batch_idx, *, max_expressions=BATCH_SIZE
):
    """Run the generator with target_category set on the field-picker, then unset."""
    set_target_category(target_category)
    try:
        elog.debug(
            "B%d: generating %d exprs for %s/%s/d%d n=%s target=%s",
            batch_idx,
            max_expressions,
            region,
            universe,
            delay,
            neutralization,
            target_category,
        )
        return generate(conn, region, delay, universe, max_expressions, neutralization=neutralization)
    finally:
        set_target_category(None)


def generate_and_submit(session, conn, batch_idx, *, max_expressions=BATCH_SIZE):
    """Pick config, generate expressions, submit batch.

    Uses pyramid3 mode: picks (region, universe, delay) AND a target_category
    weighted by pyramid completion gap x multiplier. The target steers the
    field picker so the resulting alpha lands in the targeted pyramid (filling
    pyramids that have 1-2 alphas to push them past the 3-alpha completion
    threshold, or seeding uncovered high-multiplier pyramids).
    """
    # Check before claiming a polish candidate: claiming spends its bounded
    # attempts, even when the POST later declines to run on an exhausted budget.
    if budget.is_exhausted():
        return "BUDGET"
    capacity = budget.submission_capacity(max_expressions)
    if capacity <= 0:
        return "BUDGET"

    handled, result = submit_queued_probe(session, conn, batch_idx, max_expressions=capacity)
    if handled:
        return result

    # Occasionally re-run a near-miss alpha under a different neutralization
    # instead of generating a new one (see polish.py). Checked before the
    # pyramid pick so a polish batch does not pay for a config it discards, and
    # `take_batch` returning None (empty queue, no alternative neutralization)
    # just falls through to normal generation.
    plan = None
    if polish.should_polish(batch_idx):
        if capacity < polish.POLISH_MAX_EXPRS:
            plan = polish.take_batch(conn, _rng, batch_idx, max_expressions=capacity)
        else:
            plan = polish.take_batch(conn, _rng, batch_idx)
    if plan:
        try:
            settings = plan.get("preserved_settings") or make_settings(
                plan["region"],
                plan["universe"],
                plan["delay"],
                neutralization=plan["neutralization"],
                decay=plan.get("decay"),
                truncation=plan.get("truncation"),
            )
        except Exception:
            # No POST was attempted, so this claim cannot have created work.
            release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True)
            raise
        # Only transport-level proof can return this claim: None and even a
        # later CONCURRENT/BUDGET may follow an earlier, accepted-but-unheard
        # POST. The retry loop keeps the full request history for this callback.
        return submit_batch(
            session,
            plan["expressions"],
            settings,
            batch_idx,
            conn,
            on_definitely_unsubmitted=lambda: release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True),
        )

    config, target_category = pyramid3_weighted_pick(conn, REGION_CONFIGS)
    if config is None:
        return None
    region, universe, delay = config
    neutralization = pick_neutralization(region)  # F3: pre-pick so it flows into cell_context

    exprs = _generate_with_target(
        conn,
        region,
        delay,
        universe,
        neutralization,
        target_category,
        batch_idx,
        max_expressions=capacity,
    )
    if not exprs:
        elog.debug("B%d: no expressions generated for %s/%s/d%d", batch_idx, region, universe, delay)
        return None
    settings = make_settings(region, universe, delay, neutralization=neutralization)
    return submit_batch(session, exprs, settings, batch_idx, conn)
