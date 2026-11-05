"""Reproducible probe-only drafts from the operator menu in TODO.md.

Registration waits for the ten shapes' recorded reads. These functions take
explicit scoped type pools so vector reducers cannot draw a MATRIX by name.
The range and smoothed-residual variants are controls, not extra registry slots.
"""

from dataclasses import dataclass

from generator.field_validation_pools import validation_pools
from generator.templates_brain_website_pick import (
    _RAW_VOLUME_EXCLUDE,
    _maybe_backfill,
    _pick,
    _pick_return,
    _pick_tokens,
)


@dataclass
class IdeaPools:
    matrix: tuple[str, ...]
    vectors: tuple[str, ...]
    groups: tuple[str, ...]
    pv_by_dataset: dict[str, tuple[str, ...]]


def staged_pools(conn, region, universe, delay):
    matrix, vectors, groups = validation_pools(conn, region, universe, delay)
    rows = conn.execute(
        "SELECT id, dataset_id, category_id FROM data_fields "
        "WHERE region=? AND universe=? AND delay=? AND type='MATRIX'",
        [region, universe, delay],
    ).fetchall()
    by_dataset = {}
    for field, dataset, category in rows:
        if field in matrix and dataset and category and (category == "pv" or category.startswith("pv-")):
            by_dataset.setdefault(dataset, set()).add(field)
    return IdeaPools(
        tuple(sorted(matrix)),
        tuple(sorted(vectors)),
        tuple(sorted(groups)),
        {dataset: tuple(sorted(fields)) for dataset, fields in sorted(by_dataset.items())},
    )


def vector_dispersion_stddev(pools, rng):
    if not pools.vectors:
        return None
    return f"rank(vec_stddev({rng.choice(pools.vectors)}))"


def vector_dispersion_range(pools, rng):
    if not pools.vectors:
        return None
    return f"rank(vec_range({rng.choice(pools.vectors)}))"


def density_gated_reversal(pools, rng):
    close = _pick(pools.matrix, rng, "close")
    volume = _pick_tokens(pools.matrix, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if close is None or volume is None:
        return None
    window = rng.choice((22, 60))
    return f"trade_when(less(ts_count_nans({volume}, {window}), 5), -({close} / ts_mean({close}, 60) - 1), nan)"


def last_step_momentum(pools, rng):
    field = _pick_return(pools.matrix, rng)
    if field is None:
        return None
    window = rng.choice((60, 120, 252))
    return f"rank({field} - last_diff_value({field}, {window}))"


def peer_coverage_gated_reversal(pools, rng):
    close = _pick(pools.matrix, rng, "close")
    volume = _pick_tokens(pools.matrix, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if close is None or volume is None:
        return None
    group, floor = rng.choice(("sector", "industry")), rng.choice((10, 20))
    return f"trade_when(greater(group_count({volume}, {group}), {floor}), -({close} / ts_mean({close}, 60) - 1), nan)"


def vector_residual(pools, rng):
    families = [fields for fields in pools.pv_by_dataset.values() if len(fields) >= 2]
    if not families:
        return None
    first, second = rng.sample(rng.choice(families), 2)
    return f"rank(vector_neut({_maybe_backfill(first)}, {_maybe_backfill(second)}))"


def vector_residual_smoothed(pools, rng):
    direct = vector_residual(pools, rng)
    if direct is None:
        return None
    return f"rank(ts_mean({direct[5:-1]}, 22))"


STAGED_IDEA_TEMPLATES = (
    vector_dispersion_stddev,
    density_gated_reversal,
    last_step_momentum,
    peer_coverage_gated_reversal,
    vector_residual,
)
STAGED_IDEA_CONTROLS = (vector_dispersion_range, vector_residual_smoothed)
