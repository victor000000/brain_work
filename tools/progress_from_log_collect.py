"""Parse a day of runner logs into alphas, checks, templates and polish batches.

Split out of `tools/progress_from_log.py`, which re-exports `collect` and
`passes_gate`.
"""

from collections import defaultdict

from tools.progress_from_log_patterns import (
    ALPHA_RE,
    BATCH_ALPHA_RE,
    CHECK_RE,
    CHECK_SUMMARY_RE,
    ERROR_BATCH_RE,
    FITNESS_FLOOR,
    POLISH_RE,
    REGION_DELAY_MIN_SHARPE,
    SHARPE_FLOOR,
    SHARPE_FLOOR_DEFAULT,
    TEMPLATE_RE,
    TEST_SHARPE_FLOOR,
    TURNOVER_BAND,
    TURNOVER_CEILING,
)


def collect(day: str) -> dict:
    # Imported here, not at module level: `_read` must resolve `LOG_DIR` from
    # the original module's namespace so monkeypatching `LOG_DIR` there (the
    # tests' logdir fixture) still redirects the reads.
    from tools.progress_from_log import _read

    alphas = []
    for line in _read("alpha.log", day):
        m = ALPHA_RE.match(line)
        if m:
            alphas.append(m.groupdict())
    templates = {}
    for line in _read("alpha.log", day):
        m = TEMPLATE_RE.search(line)
        if m:
            templates[m.group("id")] = m.group("name")
    checks: dict[str, list[tuple[str, str]]] = defaultdict(list)
    summaries: dict[str, dict] = {}
    for line in _read("check.log", day):
        m = CHECK_RE.search(line)
        if m:
            checks[m.group("id")].append((m.group("check"), m.group("result")))
            continue
        s = CHECK_SUMMARY_RE.search(line)
        if s:
            summaries[s.group("id")] = {
                "pass": int(s.group("p")),
                "fail": int(s.group("f")),
                "warn": int(s.group("w")),
                "pending": int(s.group("pend")),
            }
    errors = sum(1 for line in _read("errors.log", day) if ERROR_BATCH_RE.search(line))

    # Polish batches joined to the alphas they produced. The batch index is the
    # only link available, and it is NOT unique on its own: `batch_idx` starts
    # at 0 in every process, so a restarted explorer re-issues indices the
    # previous run already used. A result therefore only counts when it was
    # polled *after* the polish batch was submitted — without that, an old
    # batch's alphas are attributed to a polish batch that never produced them.
    # `alphas` also answers the sharpe for lines that do not carry one: before
    # 2026-10-09 `handle_single` wrote only "B584 alpha omWawNWl: HTTP 200", so
    # the join had an id but no sharpe. alpha.log has one line per stored alpha
    # and the id is the key, so the sharpe is recoverable for every day already
    # on disk rather than only for runs after the logging fix.
    sharpe_by_id = {a["id"]: float(a["sh"]) for a in alphas}
    by_batch: dict[str, list] = defaultdict(list)
    seen_result: set = set()
    for line in _read("poll.log", day):
        m = BATCH_ALPHA_RE.search(line)
        if not m:
            continue
        key = (m.group("idx"), m.group("id"))
        if key in seen_result:
            # A single batch now writes two matching lines — the DEBUG HTTP and
            # the INFO sharpe — and both would otherwise count once.
            continue
        sh = m.group("sh")
        sh = sharpe_by_id.get(m.group("id")) if sh is None else float(sh)
        if sh is None:
            continue  # not stored, so not produced
        seen_result.add(key)
        by_batch[m.group("idx")].append((line[:23], m.group("id"), sh))
    polish = []
    for line in _read("submit.log", day):
        m = POLISH_RE.search(line)
        if m:
            submitted_at = line[:23]
            produced = [(aid, sh) for ts, aid, sh in by_batch.get(m.group("idx"), []) if ts >= submitted_at]
            polish.append({**m.groupdict(), "produced": produced})
    return {
        "alphas": alphas,
        "templates": templates,
        "checks": checks,
        "summaries": summaries,
        "error_batches": errors,
        "polish": polish,
    }


def passes_gate(row) -> bool:
    """The local eligibility gate, as `runner/submit/eligibility.py` applies it.

    Mirrors `eligibility_clause`, out-of-sample floor included: without
    `test_sharpe > 0` this counts alphas the selector will never pick, which
    reports progress in the flattering direction.
    """
    # The exact cell's floor when the row carries a delay — the log line has
    # one — so a region whose delays differ is judged per cell rather than by
    # one region-wide number.
    try:
        floor = REGION_DELAY_MIN_SHARPE.get((row["region"], int(row["delay"])), SHARPE_FLOOR_DEFAULT)
    except (KeyError, TypeError, ValueError):
        floor = SHARPE_FLOOR.get(row["region"], SHARPE_FLOOR_DEFAULT)
    ceiling = TURNOVER_CEILING.get(row.get("region"), TURNOVER_BAND[1])
    return (
        float(row["sh"]) >= floor
        and float(row["fi"]) >= FITNESS_FLOOR
        and TURNOVER_BAND[0] <= float(row["to"]) <= ceiling
        and float(row["ts_"]) > TEST_SHARPE_FLOOR
    )
