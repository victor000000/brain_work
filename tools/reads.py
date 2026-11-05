#!/usr/bin/env python3
"""The standing pre-registered reads, printed with their thresholds.

This loop keeps asking the same handful of questions against a database that is
locked whenever the explorer runs, each time as a hand-written query. They are
collected here, with the pre-registration each one answers so the output cannot
silently drift from what was promised:

1. **The ten shapes**, each against its pre-registered sample threshold
   (recorded in `TODO.md`, 2026-10-12/14): n against threshold, median sharpe
   and floor rate per shape, with KEEP/RETIRE/INCONCLUSIVE or an exact sample shortfall.

2. **HKG's single-interval CONCENTRATED_WEIGHT rate**, split by whether the
   expression carries a timestamp-windowed field — the reading the
   `ts_backfill` wrap (live since 2026-10-15 02:58) exists to move. Baseline
   pre-wrap: 28 of 82 fragile (34%) against 1 of 14 (7%), measured 10-15.

3. **The region mix** — CHN and HKG shares — against the 2026-10-15
   pre-registration: the 5x HKG posterior tilt got its first full day on
   10-15, and if CHN holds near 8% and HKG near 20% after it, the posterior is
   not reaching the actual spend.

Usage:
    python3 tools/reads.py                     # live DB or announced snapshot fallback
    python3 tools/reads.py --db brain_data.duckdb.bak-<stamp>
"""

import argparse
import os
import statistics
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.time_sql import utc_timestamp_sql  # noqa: E402
from tools.report_db import open_report_db  # noqa: E402
from tools.shape_verdicts import SHAPE_THRESHOLDS, shape_verdict  # noqa: E402
from tools.template_report import summarize  # noqa: E402

# The ten shapes of the 2026-10-12/13 creation round, with the sample
# threshold each verdict was pre-registered at (TODO.md, "no verdict yet at
# the new backup"). `long_window` and `iv_skew` read out early by their own
# rules; the rest at 250.
SHAPES_SINCE = "2026-10-12 00:00:00"

# The backfill's before/after windows. The wrap went live with the 02:58
# restart on 10-15; anything stored from 03:00 that day is its population.
WRAP_LIVE = "2026-10-15 03:00:00"
PRE_WRAP_SINCE = "2026-10-12 00:00:00"

FRAGILE_PATTERN = "pv37_|_pre_close|_from_open|_post_open|session_[0-9]"

# The tilt's first full day, against the mix read of 2026-10-15.
MIX_WINDOWS = (
    ("pre-tilt (10-05..10-12)", "2026-10-05 00:00:00", "2026-10-12 00:00:00"),
    ("pre-5x-tilt (10-12..10-15)", "2026-10-12 00:00:00", "2026-10-15 00:00:00"),
    ("tilt day 1 (10-15 so far)", "2026-10-15 00:00:00", None),
)


def shape_reads(conn):
    rows = conn.execute(
        "SELECT template, region, delay, is_sharpe FROM alpha_results "
        f"WHERE {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP) AND template IS NOT NULL",
        [SHAPES_SINCE],
    ).fetchall()
    acc = summarize(rows)
    population = summarize([("population", region, delay, sharpe) for _, region, delay, sharpe in rows]).get(
        "population", {"sharpes": [], "at_floor": 0}
    )
    # The registered IV sample threshold explicitly counts USA cells only.
    iv_rows = [row for row in rows if row[0] == "iv_skew_reversal" and row[1] == "USA"]
    acc["iv_skew_reversal"] = summarize(iv_rows).get("iv_skew_reversal")
    print("== the ten shapes (pre-registered thresholds) ==")
    baseline = statistics.median(population["sharpes"]) if population["sharpes"] else None
    rate = population["at_floor"] / len(population["sharpes"]) if population["sharpes"] else 0
    print(
        f"population: {len(population['sharpes'])} measured labelled alphas since {SHAPES_SINCE} UTC; "
        f"median {baseline if baseline is not None else 'n/a'}; floor {rate:.2%}; IV sample USA only"
    )
    print(f"{'shape':<28} {'n':>5} {'med sh':>7} {'rate':>6}  decision")
    for name in SHAPE_THRESHOLDS:
        row = acc.get(name)
        n = len(row["sharpes"]) if row else 0
        status, reason = shape_verdict(name, row, population)
        detail = ""
        if row:
            sharpes = sorted(row["sharpes"])
            med = statistics.median(sharpes) if sharpes else None
            detail = f"{('' if med is None else f'{med:+.3f}'):>7} {(100 * row['at_floor'] / n if n else 0):>5.1f}%"
        print(f"{name:<28} {n:>5} {detail:>14}  {status}: {reason}")


def wrap_read(conn, since, until, label):
    rows = conn.execute(
        f"""
        SELECT regexp_matches(a.expression, ?) AS fragile,
               EXISTS (SELECT 1 FROM check_failures f
                       WHERE f.alpha_id = a.alpha_id AND f.check_name = 'CONCENTRATED_WEIGHT') AS cw
        FROM alpha_results a
        WHERE a.region = 'HKG' AND a.is_sharpe >= 1.58
          AND {utc_timestamp_sql("a.created_at")} >= CAST(? AS TIMESTAMP)
          AND (? IS NULL OR {utc_timestamp_sql("a.created_at")} < CAST(? AS TIMESTAMP))
        """,
        [FRAGILE_PATTERN, since, until, until],
    ).fetchall()
    for fragile in (True, False):
        sel = [r for r in rows if r[0] is fragile]
        fails = sum(1 for r in sel if r[1])
        rate = f"{100 * fails / len(sel):.0f}%" if sel else "-"
        print(f"  {label}  fragile={fragile!s:<5} n={len(sel):>3}  CW fails={fails:>2}  {rate}")


def mix_reads(conn):
    print("== region mix (the 5x HKG tilt read) ==")
    for label, lo, hi in MIX_WINDOWS:
        total = conn.execute(
            f"SELECT count(*) FROM alpha_results WHERE {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP) "
            f"AND (? IS NULL OR {utc_timestamp_sql('created_at')} < CAST(? AS TIMESTAMP))",
            [lo, hi, hi],
        ).fetchone()[0]
        if not total:
            print(f"  {label}: no rows yet")
            continue
        parts = []
        for region in ("CHN", "HKG"):
            n = conn.execute(
                "SELECT count(*) FROM alpha_results WHERE region = ? "
                f"AND {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP) "
                f"AND (? IS NULL OR {utc_timestamp_sql('created_at')} < CAST(? AS TIMESTAMP))",
                [region, lo, hi, hi],
            ).fetchone()[0]
            parts.append(f"{region} {n} ({100 * n / total:.1f}%)")
        print(f"  {label}: n={total}  " + "  ".join(parts))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.path.join(PROJECT_DIR, "brain_data.duckdb"), help="database to read")
    args = ap.parse_args()

    conn, args.db = open_report_db(args.db)
    try:
        print(f"db: {os.path.basename(args.db)}   {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
        print()
        shape_reads(conn)
        print()
        print("== HKG CONCENTRATED_WEIGHT, fragile-field split (the backfill read) ==")
        wrap_read(conn, PRE_WRAP_SINCE, WRAP_LIVE, "pre-wrap ")
        wrap_read(conn, WRAP_LIVE, None, "post-wrap")
        print()
        mix_reads(conn)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
