#!/usr/bin/env python3
"""Validate the staged operator menu offline; never register or post a probe."""

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_DIR = str(Path(__file__).resolve().parents[1])
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.regions import REGION_CONFIGS  # noqa: E402
from generator.field_picker import get_cache  # noqa: E402
from generator.idea_templates_staged import STAGED_IDEA_CONTROLS, STAGED_IDEA_TEMPLATES, staged_pools  # noqa: E402
from generator.template_fill import filled_expression_problem  # noqa: E402
from generator.validate import load_operator_names  # noqa: E402
from tools.report_db import open_report_db  # noqa: E402


def sweep(conn, renders, seed):
    templates = (*STAGED_IDEA_TEMPLATES, *STAGED_IDEA_CONTROLS)
    totals = {fn.__name__: {"renders": 0, "invalid": 0, "empty_cells": [], "samples": []} for fn in templates}
    operators = load_operator_names(conn)
    cache = get_cache()
    previous_cell = cache.last_loaded
    try:
        for region, universe, delay in REGION_CONFIGS:
            pools = staged_pools(conn, region, universe, delay)
            # The HKG coverage wrapper uses only this cell marker. No random
            # generation cap or global field list participates in the draft.
            cache.last_loaded = (region, delay, universe)
            for index, fn in enumerate(templates):
                result = totals[fn.__name__]
                rng = random.Random(seed + index)
                emitted = 0
                for _ in range(renders):
                    expr = fn(pools, rng)
                    if expr is None:
                        continue
                    emitted += 1
                    result["renders"] += 1
                    problem = filled_expression_problem(expr, pools.matrix, operators, pools.vectors, pools.groups)
                    if problem:
                        result["invalid"] += 1
                        if len(result["samples"]) < 3:
                            result["samples"].append({"expression": expr, "problem": problem})
                if not emitted:
                    result["empty_cells"].append([region, universe, delay])
    finally:
        cache.last_loaded = previous_cell
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="database or snapshot")
    parser.add_argument("--renders", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", help="save the audit as JSON")
    args = parser.parse_args(argv)
    if args.renders < 1:
        parser.error("--renders must be positive")
    conn, source = open_report_db(args.db)
    try:
        totals = sweep(conn, args.renders, args.seed)
    finally:
        conn.close()
    report = {
        "db": source,
        "seed": args.seed,
        "renders_per_cell": args.renders,
        "registration": "waiting for the ten shapes' registered reads",
        "templates": totals,
    }
    output = json.dumps(report, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n")
    print(output)
    return int(any(row["invalid"] or row["empty_cells"] for row in totals.values()))


if __name__ == "__main__":
    raise SystemExit(main())
