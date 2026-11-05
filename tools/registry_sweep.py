#!/usr/bin/env python3
"""Render every registered template in every configured cell and validate it.

The check `TODO.md` calls the sweep, made durable: each template renders N
times per (region, universe, delay), and every render is validated with
`filled_expression_problem` — syntax, operator allowlist, field membership and
the field-type contracts. It closes the two failure modes this project has been
bitten by more than once: a template that is *unselectable* in some cell
(`d75bcaf`, 21 of 38), and a template that emits invalid syntax somewhere.

It earns its keep. On 2026-10-12 it caught `hump(x, 0.05)` failing every
render — the platform defines `hump(x, hump = 0.01)`, so the second parameter
is keyword-only — and on 2026-10-13 the same class again, a named argument
whose key the token scanner read as a field. Both would have cost simulations
in the batch path.

**The harness is as likely to be wrong as the code it measures.** The first
run of this sweep reported 9,750 invalid renders that were its own bug: the two
pool-based templates take `(f1, f2)`, not `(fields, rng)`, and calling them the
pool way passes the field list as one operand. `registry.template_uses_pool`
exists to dispatch exactly that, and the call below honours it. Before
believing a sweep result, check whether the harness asked the right question.

Runs against a **backup** by default, because the live database is locked
whenever the explorer is up — including while it parks on an exhausted budget,
so the lock is not released by waiting. Cells whose fields are absent from the
backup's vintage contribute nothing and are reported as never-emitting; check
`data_fields` for the cell before reading that as a template defect. The
2026-10-03 backup had four such cells (AMR/TOP600 both delays, DEU/TOP500/d1,
GBR/TOP700/d1); the 2026-10-13 backup taken after them has none, so the only
expected non-emitters there are the options shapes outside USA/IND.

Usage:
    python3 tools/registry_sweep.py                       # all templates, 25 renders/cell
    python3 tools/registry_sweep.py --only dual_bucket    # one template by name fragment
    python3 tools/registry_sweep.py --db brain_data.duckdb --renders 10
"""

import argparse
import os
import random
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.regions import REGION_CONFIGS  # noqa: E402
from generator.field_picker import load_all_fields  # noqa: E402
from generator.random_generator_pools import prepare_pools  # noqa: E402
from generator.registry import ALL_TEMPLATES, template_uses_pool  # noqa: E402
from generator.template_fill import filled_expression_problem  # noqa: E402
from generator.templates_brain_website_pick import _maybe_backfill  # noqa: E402
from tools.report_db import open_report_db  # noqa: E402

DEFAULT_DB = os.path.join(PROJECT_DIR, "brain_data.duckdb")


def render(fn, fields, rng):
    """One render, under the template's own calling convention.

    Getting this wrong is the 2026-10-11 false alarm: a `(fields, rng)`
    template called the two-field way raises inside itself (`'str' object has
    no attribute 'choice'`) and reads as a template that never emits.
    """
    if template_uses_pool(fn):
        return fn(fields, rng)
    if len(fields) < 2:
        return None
    # Mirrors `random_generator_dispatch._call_template`: the generator
    # wraps HKG interval fields here, so the sweep must validate what it
    # emits.
    return fn(_maybe_backfill(rng.choice(fields)), _maybe_backfill(rng.choice(fields)))


def sweep_cell(
    templates, field_pool, vector_fields, group_fields, known_ops, renders, validate=filled_expression_problem
):
    """Render every template in one cell. Returns (count, invalid, never).

    `invalid` is a list of `(template_name, problem, expression)` and `never`
    the names that produced nothing — kept as data rather than printed so a
    caller (or a test) can act on them.
    """
    count, invalid, never = 0, [], []
    for idx, (fn, _ops) in enumerate(templates):
        rng = random.Random(1000 + idx)
        emitted = 0
        for _ in range(renders):
            expr = render(fn, field_pool, rng)
            if not expr:
                continue
            emitted += 1
            count += 1
            problem = validate(expr, field_pool, known_ops, vector_fields, group_fields)
            if problem is not None:
                invalid.append((fn.__name__, str(problem), expr))
        if emitted == 0:
            never.append(fn.__name__)
    return count, invalid, never


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--renders", type=int, default=25, help="renders per template per cell")
    ap.add_argument(
        "--db", default=DEFAULT_DB, help="database to sweep (default: live, with announced snapshot fallback)"
    )
    ap.add_argument("--only", default=None, help="substring filter on template names")
    ap.add_argument("--max-print", type=int, default=20, help="invalid renders to print in full")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="also fail when a cell/template pair never emitted (only meaningful against the live database)",
    )
    args = ap.parse_args()
    if args.renders < 1 or args.max_print < 0:
        ap.error("--renders must be positive and --max-print must be nonnegative")

    conn, args.db = open_report_db(args.db)
    try:
        return run_sweep(conn, args)
    finally:
        conn.close()


def run_sweep(conn, args):
    templates = [(fn, ops) for fn, ops in ALL_TEMPLATES if not args.only or args.only in fn.__name__]
    print(f"db: {os.path.basename(args.db)}")
    print(f"templates: {len(templates)} of {len(ALL_TEMPLATES)}   renders/cell: {args.renders}")

    total, invalid_count, printed, never = 0, 0, 0, []
    for region, universe, delay in REGION_CONFIGS:
        load_all_fields(conn, region, delay, universe)
        _cache, field_pool, vector_fields, group_fields, known_ops, _mix = prepare_pools(conn)
        count, invalid, cell_never = sweep_cell(
            templates, field_pool, vector_fields, group_fields, known_ops, args.renders
        )
        total += count
        invalid_count += len(invalid)
        for name, problem, expr in invalid:
            if printed < args.max_print:
                print(f"INVALID {region}/{universe}/d{delay} {name}: {problem}")
                print(f"        {expr[:170]}")
                printed += 1
        never.extend((region, universe, delay, name) for name in cell_never)

    print()
    print(f"cells swept            : {len(REGION_CONFIGS)}")
    print(f"renders validated      : {total}")
    print(f"invalid renders        : {invalid_count}")
    print(f"cell/template pairs that never emitted: {len(never)}")
    for row in never[:25]:
        print("   ", row)
    if never:
        print()
        print("never-emitting pairs are usually data rather than a template defect — a cell")
        print("whose fields are absent from this backup's vintage, or a template needing a")
        print("field family the cell does not have (options templates outside USA/IND). Check")
        print("`data_fields` for the cell before reading one as a defect.")

    # Invalid renders are the defect this tool exists to catch, and fail the
    # run. Never-emitting pairs fail it only under --strict, where the caller
    # has asserted the database is current enough that absence means something:
    # a historical backup may legitimately lack an entire cell.
    if invalid_count:
        return 1
    return 1 if (never and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
