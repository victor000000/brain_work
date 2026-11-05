#!/usr/bin/env python3
"""Mine shapes from alphas that reached their own cell's submission floor.

The corpora we mine are exhausted: the forum was re-crawled on 2026-10-11 and
produced 13 new posts and zero new fillable skeletons, `cnhkmcp` is 99% out of
scope, and the help centre and learn docs have not changed. `proven_templates`
is the one corpus drawn from *results* rather than prose — 52 shapes from the 40
alphas the platform accepted — and it is the only one that measures like the
built-ins (2.04% at the floor against 0.25% for `forum`).

Its supply is tiny because acceptance is rare. The floor is not: 1,842 alphas
have reached their cell's floor, against 40 accepted. This mines those.

A skeleton is the expression with every **known field** replaced by `{f}` and
nothing else changed, so literal windows (`60`, `252`) stay: they are part of
the shape, and the fill-time validator checks the result either way. Rows whose
skeleton still contains an identifier that is neither an operator, a built-in
group/argument name nor a `{f}` slot are dropped — that means the expression
read a field we no longer hold (the database was narrowed to pv/option on
2026-10-02), and the pool would reject them anyway.

`--min-evidence` is the reproducibility bar: how many above-floor alphas must
share the shape before it is written. The default of 2 leaves 46 of the 132
net-new shapes; the rest rest on a single observation each. Lower it if the
corpus measures well, raise it if it does not — `template_performance` labels
these `pool:provenfloor` and the corpus prior will weigh them on their record
like any other corpus.

Usage:
    python3 tools/mine_proven_floor.py [--days 30] [--min-evidence 2] [--dry-run]
"""

import argparse
import collections
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import DB_PATH, connect_for_reading  # noqa: E402
from core.time_sql import utc_timestamp_sql  # noqa: E402
from generator.template_fill_tokens import GROUP_NAMES, KEYWORDS  # noqa: E402
from generator.validate import called_identifiers, load_operator_names  # noqa: E402
from runner.submit.eligibility import REGION_DELAY_MIN_SHARPE  # noqa: E402

OUT_PATH = os.path.join(PROJECT_DIR, "docs", "forum", "proven_floor_templates.json")
DEFAULT_FLOOR = 1.58
_TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def _floor(region, delay):
    return REGION_DELAY_MIN_SHARPE.get((region, delay), DEFAULT_FLOOR)


def mine(conn, days=30, min_evidence=2):
    """Rows for every shape with enough above-floor evidence."""
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    vocab = {row[0] for row in conn.execute("SELECT DISTINCT id FROM data_fields").fetchall() if row[0]}
    operators = load_operator_names(conn)
    allowed_tokens = operators | vocab | GROUP_NAMES | KEYWORDS
    alphas = conn.execute(
        f"""
        SELECT region, delay, universe, expression, is_sharpe
        FROM alpha_results
        WHERE expression IS NOT NULL AND is_sharpe IS NOT NULL
          AND {utc_timestamp_sql("created_at")} >= CAST(? AS TIMESTAMP)
        """,
        (since,),
    ).fetchall()

    shapes = collections.defaultdict(lambda: {"n": 0, "best": 0.0, "example": "", "fields": set()})
    for region, delay, _universe, expression, sharpe in alphas:
        if sharpe < _floor(region, delay):
            continue
        tokens = _TOKEN.findall(expression)
        # Drop anything that reads a field we no longer hold: the pool would
        # reject it, and keeping it would put unscopable text in the corpus.
        # Built-in groups and named arguments/literals (std, range, nan, ...)
        # remain valid even when they are not present in the field metadata.
        if set(tokens) - allowed_tokens:
            continue
        # Allowing a built-in as a value must not allow it to be called as an
        # operator: industry(close) and std(close) are still invalid shapes.
        if called_identifiers(expression) - operators:
            continue
        skeleton = _TOKEN.sub(lambda m: "{f}" if m.group(0) in vocab else m.group(0), expression)
        row = shapes[skeleton]
        row["n"] += 1
        row["fields"].update(t for t in tokens if t in vocab)
        if sharpe > row["best"]:
            row["best"] = sharpe
            row["example"] = expression

    rows = []
    for skeleton, row in sorted(shapes.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        if row["n"] < min_evidence:
            continue
        rows.append(
            {
                "skeleton": skeleton,
                "posts": 0,
                "example": row["example"],
                "pv_option_fields": sorted(row["fields"]),
                "other_fields": [],
                "fillable_from_pv_option": True,
                "found_in": ["floor"],
                "alpha_count": row["n"],
                "best_sharpe": round(row["best"], 2),
                "topic": f"floor: {row['n']} above-floor alpha(s) share this shape, best sharpe {row['best']:.2f}",
                "html_url": "",
            }
        )
    return rows, len(shapes), len(alphas)


def main(conn=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        default=None,
        help="DuckDB file to mine (default: the live brain_data.duckdb). Point it at a "
        "backup to re-mine while the explorer holds the lock, as the other miners allow.",
    )
    parser.add_argument("--days", type=int, default=30, help="window over alpha_results.created_at")
    parser.add_argument("--min-evidence", type=int, default=2, help="above-floor alphas a shape needs")
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = parser.parse_args()

    owns = conn is None
    # Mining is read-only, and it is the tool most likely to be wanted while the
    # explorer is running — it is the corpus that measures like the built-ins.
    # The other three miners (`mine_forum_templates`, `mine_help_center_templates`,
    # `parse_cnhkmcp_templates`) all take `--db` for exactly this; this one did
    # not, so a live explorer meant no re-mine at all, which is backwards for the
    # only corpus whose supply comes from results rather than from prose.
    conn = conn or connect_for_reading(args.db or DB_PATH)
    try:
        rows, shapes, alphas = mine(conn, days=args.days, min_evidence=args.min_evidence)
    finally:
        if owns:
            conn.close()

    print(f"scanned {alphas:,} alphas in the last {args.days}d: {shapes} distinct shapes")
    print(f"writing {len(rows)} with >= {args.min_evidence} above-floor alpha(s)")
    for r in rows[:10]:
        print(f"  {r['alpha_count']:>4}x best={r['best_sharpe']:<6} {r['skeleton'][:88]}")
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    with open(OUT_PATH, "w") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
