"""Render a day's collected log data, and the CLI that drives the summary.

Split out of `tools/progress_from_log.py`, which re-exports `report` and
`main`.
"""

import sys
from collections import Counter
from datetime import UTC, datetime

from tools.progress_from_log_collect import collect, passes_gate


def report(day: str, data: dict, out=print) -> None:
    rows = data["alphas"]
    sh = [float(r["sh"]) for r in rows]
    out(f"=== {day}: {len(rows)} alphas stored ===")
    if not rows:
        out("  (no alpha.log lines for this day)")
        return
    out(f"  sharpe >= 1.58 : {sum(1 for x in sh if x >= 1.58)}")
    out(f"  sharpe >= 1.0  : {sum(1 for x in sh if x >= 1.0)}")
    out(f"  sharpe > 0     : {sum(1 for x in sh if x > 0)}")
    out(f"  best sharpe    : {max(sh):.2f}   worst: {min(sh):.2f}")

    gate = sorted((r for r in rows if passes_gate(r)), key=lambda r: -float(r["sh"]))
    checked = data["checks"]
    summaries = data["summaries"]
    out(f"\n=== {len(gate)} pass the local gate (sharpe/fitness/turnover/test sharpe) ===")
    for r in gate:
        fails = [c for c, res in checked.get(r["id"], []) if res == "FAIL"]
        s = summaries.get(r["id"])
        if s:
            verdict = f"P={s['pass']} F={s['fail']} W={s['warn']} Pend={s['pending']}"
        elif checked.get(r["id"]):
            verdict = "checked (no summary line)"
        else:
            verdict = "not yet checked"
        if fails:
            verdict += f" — FAIL: {', '.join(fails)}"
        tmpl = data["templates"].get(r["id"], "?")
        out(
            f"  {r['id']:10} sh={r['sh']:>6} fi={r['fi']:>6} to={r['to']:>7} "
            f"{r['region']}/{r['uni']}/d{r['delay']} {r['neut']:<20} [{tmpl}]"
        )
        out(f"      {verdict}")

    out("\n=== regions ===")
    by_region = Counter((r["region"], r["uni"]) for r in rows)
    for (reg, uni), n in by_region.most_common(10):
        best = max(float(r["sh"]) for r in rows if r["region"] == reg and r["uni"] == uni)
        out(f"  {reg}/{uni:16} {n:>5}  best_sh={best:.2f}")

    tmpl_counts = Counter(data["templates"].values())
    if tmpl_counts:
        out("\n=== templates ===")
        for name, n in tmpl_counts.most_common(12):
            out(f"  {name:34} {n:>5}")

    polish = data.get("polish") or []
    if polish:
        out("\n=== polish batches (near-miss re-runs) ===")
        for p in polish:
            best = max((s for _, s in p["produced"]), default=None)
            out(f"  B{p['idx'] or '?'}: {p['ids']} -> {p['region']}/{p['uni']}/d{p['delay']} under {p['neut']}")
            produced = ", ".join(f"{aid}({sh:+.2f})" for aid, sh in p["produced"]) or "no results yet"
            out(f"      {len(p['produced'])} produced: {produced}")
            if best is not None:
                out(f"      best sharpe {best:+.2f}")

    out(f"\n  platform-errored batches: {data['error_batches']}")
    if data["error_batches"]:
        total_batches = len(rows) // 10 + data["error_batches"]
        out(f"  batch error rate       : {data['error_batches'] / max(total_batches, 1):.1%}")


def main() -> int:
    # Log timestamps are UTC (see TODO: all DB and log timestamps are UTC), so
    # "today" has to be UTC too or the evening's lines land on tomorrow's date.
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(UTC).strftime("%Y-%m-%d")
    report(day, collect(day))
    return 0
