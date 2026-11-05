"""Debug the random alpha generator — local validation."""

import sys

from core.db import get_conn
from core.regions import REGION_CONFIGS
from generator.random_generator import generate_expressions
from generator.registry import ALL_TEMPLATES
from tools.debug.validate import check_expression

sys.stdout.reconfigure(line_buffering=True)

N_PER_REGION = 10


def main():
    conn = get_conn()
    print(f"Templates: {len(ALL_TEMPLATES)}")

    total_ok, total_fail = 0, 0

    for region, universe, delay in REGION_CONFIGS:
        exprs = generate_expressions(conn, region, delay, universe, N_PER_REGION)
        if not exprs:
            print(f"\n{region}/{universe}/d{delay}: NO FIELDS")
            continue

        valid_fields = set(
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT id FROM data_fields WHERE region=? AND delay=?", (region, delay)
            ).fetchall()
        )

        ok, fail = 0, 0
        for expr in exprs:
            err = check_expression(expr, valid_fields)
            if err:
                fail += 1
                total_fail += 1
                print(f"  FAIL {err}: {expr[:60]}")
            else:
                ok += 1
                total_ok += 1

        print(f"{region}/{universe}/d{delay}: {ok}/{len(exprs)} ok ({len(valid_fields)} fields)")

    total = total_ok + total_fail
    print(f"\n=== {total_ok}/{total} OK ({total_ok / total * 100:.0f}%) ===" if total else "")
    conn.close()


if __name__ == "__main__":
    main()
