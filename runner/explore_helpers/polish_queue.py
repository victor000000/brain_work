"""Claim one cell's worth of near-miss candidates for a polish batch.

Split out of `runner/explore_helpers/polish.py`, which re-exports `take_batch`.
"""

import collections

from core.log import get_file_logger
from generator.weighted_selection import record_expr_template
from runner.explore_helpers.polish_cell import pick_cell
from runner.explore_helpers.polish_language import preserve_python_batch
from runner.explore_helpers.polish_weights import outcome_weights

plog = get_file_logger("submit")


def _restore_provenance(conn, cands):
    """Re-record `expr -> template` for candidates re-submitted from the queue.

    `polish_candidates` stores no template name, but its `alpha_id` points at
    the row that does. Without this a polished alpha comes back under a name
    nothing weights: the generator's map is keyed by expression string and is
    in-memory, so the recording made when the expression was first generated —
    days earlier, in a previous process, or long since FIFO-evicted — is gone
    by the time the candidate is polished. `unknown` feeds neither
    `template_performance` nor the correlation prior, so those alphas were
    invisible to both.

    Measured 2026-10-10: 82 `unknown` alphas that day, four of them at the
    sharpe floor including a 3.22 gate-passer, and the plain-arithmetic
    samples are the price templates — which is exactly the polish corpus.
    """
    ids = [c[0] for c in cands if c[0]]
    if not ids:
        return
    # Ask the catalog before selecting from the table. A failing statement
    # aborts the surrounding transaction in DuckDB, so the bare try/except this
    # started as did not merely lose the provenance lookup — it discarded the
    # `attempts` update that ran before it, and `test_take_batch_increments_attempts`
    # caught exactly that. A catalog read on a table that may lack the column
    # cannot fail that way, and a schema without `template` has nothing to
    # restore anyway.
    try:
        has_column = conn.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'alpha_results' AND column_name = 'template'"
        ).fetchone()[0]
        if not has_column:
            return
        rows = conn.execute(
            f"SELECT alpha_id, template FROM alpha_results WHERE alpha_id IN ({','.join('?' * len(ids))})",
            ids,
        ).fetchall()
    except Exception as e:  # a pre-migration schema
        plog.debug("provenance restore unavailable: %s", e)
        return
    by_id = {aid: name for aid, name in rows if name and name != "unknown"}
    for cand in cands:
        name = by_id.get(cand[0])
        if name:
            record_expr_template(cand[1], name)


def _original_settings(conn, alpha_ids):
    """`{(decay, truncation)}` for the alphas a batch's candidates came from.

    The polish row holds the cell and the neutralization but not these two, and
    the settings axis must not re-run a candidate under its own pair. A missing
    row yields nothing, which only makes the pick slightly less careful.
    """
    if not alpha_ids:
        return set()
    try:
        rows = conn.execute(
            f"SELECT decay, truncation FROM alpha_results WHERE alpha_id IN ({','.join('?' * len(alpha_ids))})",
            list(alpha_ids),
        ).fetchall()
    except Exception as e:  # table absent on an old DB
        plog.debug("original settings unavailable: %s", e)
        return set()
    return {(d, t) for d, t in rows if d is not None and t is not None}


def take_batch(conn, rng=None, batch_idx=None, *, max_expressions=None):
    """Claim one cell's worth of near-miss candidates, or None.

    Returns a dict with the expressions, their cell, the variant neutralization
    and the alpha ids it consumed. Attempts are reserved here and remain
    charged unless the caller proves no simulation could have been accepted.
    A receipt permits that exact reservation to be released on a definite
    rejection; transport ambiguity and accepted requests retain the charge.

    `batch_idx` is carried into the log line only: it is what makes the batch's
    results attributable afterwards, since `simulate.log` maps every batch to
    the alphas it produced (`B<idx> alpha <alpha_id>`). Without it a polished
    alpha is indistinguishable from a freshly generated one and the experiment
    cannot be evaluated.
    """
    # Local import: polish.py re-exports this function, so a module-level import would cycle.
    from runner.explore_helpers.polish import (
        POLISH_EVERY,
        POLISH_MAX_ATTEMPTS,
        POLISH_MAX_EXPRS,
        POLISH_SETTINGS_EVERY,
        _rng,
        format_settings_tried,
        tries_neutralization,
        variant_neutralization,
        variant_settings,
    )

    rng = rng or _rng
    try:
        rows = conn.execute(
            """SELECT alpha_id, expression, region, universe, delay, neutralization, attempts, tried
               FROM polish_candidates WHERE attempts < ?
               ORDER BY attempts, created_at, alpha_id""",
            (POLISH_MAX_ATTEMPTS,),
        ).fetchall()
    except Exception as e:  # table absent on a pre-migration DB
        plog.debug("polish queue unavailable: %s", e)
        return None
    if not rows:
        return None

    # Which cell this batch runs in, and which candidates: the rotation that
    # keeps every cell's near-misses moving, plus the cross-cell axis that
    # re-runs a candidate somewhere it has not saturated. See `polish_cell`.
    limit = POLISH_MAX_EXPRS if max_expressions is None else min(POLISH_MAX_EXPRS, max_expressions)
    if limit <= 0:
        return None
    # Resolve language before the FASTEXPR cross-cell parser sees the source.
    (region, universe, delay), cands = pick_cell(conn, rows, limit, rng, None)
    (region, universe, delay), cands, preserved_settings = preserve_python_batch(conn, (region, universe, delay), cands)
    if preserved_settings is None:
        (region, universe, delay), cands = pick_cell(conn, cands, limit, rng, batch_idx)

    # The whole batch runs under one set of settings, so the variant has to be
    # new for every candidate in it, not just the first: one any of them has
    # already been simulated under would repeat that simulation exactly.
    tried = {n for c in cands for n in (c[7] or "").split(",") if n and tries_neutralization(n)}

    neut = decay = truncation = None
    if batch_idx is not None and (batch_idx // POLISH_EVERY) % POLISH_SETTINGS_EVERY == 1:
        # Settings axis. It needs candidates that share their *original*
        # neutralization, because the batch carries one value: varying both
        # axes at once loses the attribution the measurement above depends on.
        # Most batches are same-cell near-misses of the same shape, so this
        # usually holds; when it does not, the neutralization axis is used.
        shared = collections.Counter(c[5] for c in cands if c[5]).most_common(1)[0][0] if cands else None
        subset = [c for c in cands if c[5] == shared] if shared else []
        pair = None
        if subset:
            # The polish row does not carry decay/truncation; the alpha the
            # candidate came from does. Without them the pick could land on the
            # candidate's own settings, which is the identical simulation the
            # `tried` column exists to prevent.
            originals = _original_settings(conn, [c[0] for c in subset])
            pair = variant_settings(
                rng,
                tried={n for c in subset for n in (c[7] or "").split(",") if n},
                originals=originals,
            )
        if pair:
            cands, neut, (decay, truncation) = subset, shared, pair

    if neut is None:
        neut = variant_neutralization(region, cands[0][5], rng, weights=outcome_weights(conn), tried=tried)
        if neut is None:
            plog.debug("no alternative neutralization for %s — skipping polish", region)
            return None

    if preserved_settings is not None:
        preserved_settings["neutralization"] = neut
        if decay is not None:
            preserved_settings.update(decay=decay, truncation=truncation)

    entry = neut if decay is None else format_settings_tried(decay, truncation)
    receipt = {"entries": [], "settled": False}
    for cand in cands:
        # Record the variant so the next attempt for this candidate cannot
        # repeat it — same expression, same cell, so it would be identical.
        already = cand[7] or ""
        merged = ",".join(filter(None, [already, entry]))
        conn.execute(
            "UPDATE polish_candidates SET attempts = attempts + 1, tried = ? WHERE alpha_id = ?", (merged, cand[0])
        )
        receipt["entries"].append(
            {
                "alpha_id": cand[0],
                "expression": cand[1],
                "attempts_before": cand[6],
                "tried_before": already,
                "attempts_after": cand[6] + 1,
                "tried_after": merged,
            }
        )
    conn.commit()

    plog.info(
        "B%s: polishing %d near-miss alpha(s) in %s/%s/d%d under %s: %s",
        batch_idx if batch_idx is not None else "?",
        len(cands),
        region,
        universe,
        delay,
        neut,
        ", ".join(c[0] for c in cands),
    )
    # After the commit, so a restore that goes wrong cannot take the attempt
    # bookkeeping with it.
    _restore_provenance(conn, cands)
    return {
        "expressions": [c[1] for c in cands],
        "region": region,
        "universe": universe,
        "delay": delay,
        "neutralization": neut,
        # Set only on the settings axis; the caller passes them through to
        # `make_settings`, which otherwise draws them as usual.
        "decay": decay,
        "truncation": truncation,
        "alpha_ids": [c[0] for c in cands],
        "claim_receipt": receipt,
        "preserved_settings": preserved_settings,
    }
