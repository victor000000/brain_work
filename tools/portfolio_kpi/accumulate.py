"""Accumulate per-population stats from alpha_results."""

import json

from tools._kpi_helpers import is_atom_by_dataset


def _atom_by_dataset_count(raw_json_str):
    """1 if the alpha is atomic by dataset (per BRAIN classification), else 0."""
    if not raw_json_str:
        return 0
    try:
        raw = json.loads(raw_json_str)
    except json.JSONDecodeError:
        return 0  # malformed raw_json -> not atomic by this definition
    return 1 if is_atom_by_dataset(raw) else 0


def _parse_pyramid_categories(pyr_json):
    if not pyr_json:
        return []
    try:
        return json.loads(pyr_json)
    except json.JSONDecodeError:
        return []


def accumulate_population(conn, where_clause: str) -> dict:
    """Read one population, return {N, A_dataset, A_category, per_pyramid}.

    per_pyramid[category] = number of alphas in this population that include
    `category` in their pyramid_categories list. Multi-category alphas
    contribute to each category they belong to.
    """
    n = a_dataset = a_category = 0
    per_pyramid: dict[str, int] = {}

    rows = conn.execute(f"SELECT raw_json, pyramid_categories FROM alpha_results WHERE {where_clause}").fetchall()
    for raw_json_str, pyr_json in rows:
        n += 1
        a_dataset += _atom_by_dataset_count(raw_json_str)
        cats = _parse_pyramid_categories(pyr_json)
        if len(cats) == 1:
            a_category += 1
        for c in cats:
            per_pyramid[c] = per_pyramid.get(c, 0) + 1

    return {
        "N": n,
        "A_dataset": a_dataset,
        "A_category": a_category,
        "per_pyramid": per_pyramid,
    }
