"""Stored alpha and submission counts, read without taking a writer lock."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.time_sql import utc_timestamp_sql
from tools.report_db import open_report_db


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="database or snapshot (default: live, with announced snapshot fallback)")
    parser.add_argument("--day", default=datetime.now(UTC).date().isoformat(), help="creation date in UTC")
    parser.add_argument("--limit", type=int, default=10, help="maximum recorded submissions to list")
    args = parser.parse_args(argv)
    try:
        start = datetime.strptime(args.day, "%Y-%m-%d")
    except ValueError:
        parser.error("--day must be a UTC date in YYYY-MM-DD format")
    if args.limit < 1:
        parser.error("--limit must be positive")
    end = start + timedelta(days=1)
    stamp = utc_timestamp_sql("created_at")
    conn, source = open_report_db(args.db)
    try:
        total, submitted = conn.execute(
            "SELECT COUNT(*), COUNT(*) FILTER (WHERE status='SUBMITTED') FROM alpha_results"
        ).fetchone()
        day_total, day_submitted = conn.execute(
            "SELECT COUNT(*), COUNT(*) FILTER (WHERE status='SUBMITTED') FROM alpha_results "
            f"WHERE {stamp} >= CAST(? AS TIMESTAMP) AND {stamp} < CAST(? AS TIMESTAMP)",
            [start, end],
        ).fetchone()
        recent = conn.execute(
            "SELECT alpha_id, is_sharpe, is_fitness, region, universe, neutralization, created_at "
            f"FROM alpha_results WHERE status='SUBMITTED' ORDER BY {stamp} DESC NULLS LAST, alpha_id LIMIT ?",
            [args.limit],
        ).fetchall()
    finally:
        conn.close()
    print(f"db: {Path(source).name}")
    print(f"Stored alpha results: {total}")
    print(f"Recorded submissions: {submitted}")
    print(f"Created {args.day} UTC: {day_total} alpha results, {day_submitted} recorded submissions")
    for alpha_id, sharpe, fitness, region, universe, neutralization, created_at in recent:
        sharpe_text = "n/a" if sharpe is None else f"{sharpe:.4f}"
        fitness_text = "n/a" if fitness is None else f"{fitness:.4f}"
        print(
            f"  {alpha_id}: sharpe={sharpe_text}, fitness={fitness_text}; {region}/{universe}/{neutralization}; created {created_at}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
