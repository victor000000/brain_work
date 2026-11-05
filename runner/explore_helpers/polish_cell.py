"""Which cell a polish batch runs in.

Split out of `runner/explore_helpers/polish_queue.py`, which re-exports
`pick_cell`.

Two things decide the cell. The rotation is the older half: least-worked cell
first, so every cell with a near-miss gets its turn — taking the most-populated
cell instead starved the rest permanently, and 110 of the 124 polish batches on
2026-10-05/06 went to HKG/TOP800/d1 while one-fail alphas elsewhere were never
re-run at all.

The cross-cell axis is the newer half, and it is the one that answers the
saturation problem: `polish_crosscell.cross_cell_target` moves a batch to a cell
the candidate has not been tried in, every `CROSS_CELL_EVERY` batches.
"""

from runner.explore_helpers.polish_crosscell import CROSS_CELL_EVERY, cross_cell_target


def pick_cell(conn, rows, max_exprs, rng, batch_idx):
    """The cell (region, universe, delay) and candidates for one polish batch.

    `rows` are `polish_candidates` rows, least-attempted first, so coverage
    spreads across the whole queue before any candidate gets a second variant.
    Ordering by `created_at` alone re-ran the same oldest few four times each —
    the same three candidates went out twice in a row under different
    neutralizations — which spends the budget on one idea instead of sampling
    many.

    The measure is attempts *per candidate*, not the cell's total: a total
    penalises a cell for being large, and HKG's 70 candidates would then be
    outranked by any single untouched one forever. The average lets the small
    cells cycle (each candidate retires after POLISH_MAX_ATTEMPTS and leaves
    the pool) without locking the big one out. Ties go to the larger cell, so a
    batch is still as full as the queue allows.
    """
    by_cell: dict[tuple, list] = {}
    for row in rows:
        by_cell.setdefault((row[2], row[3], row[4]), []).append(row)
    cell, cands = min(
        by_cell.items(),
        key=lambda kv: (sum(c[6] for c in kv[1]) / len(kv[1]), -len(kv[1]), kv[0]),
    )
    cands = cands[:max_exprs]
    if batch_idx is not None and batch_idx % CROSS_CELL_EVERY == 0:
        target = cross_cell_target(conn, [c[1] for c in cands], cell, rng)
        if target is not None:
            return target, cands
    return cell, cands
