"""The rendered progress report: summaries, errors and polish batches."""

from tests.test_progress_from_log_helpers import ALPHA_OK, _write, logdir
from tools import progress_from_log as p

# The fixture is re-exported: pytest finds it by name in this module's namespace.
__all__ = ["logdir"]


def test_check_summary_and_failed_checks_are_reported(logdir, capsys):
    _write(logdir, "alpha.log", [ALPHA_OK])
    _write(
        logdir,
        "check.log",
        [
            "2026-10-05 08:39:16,006 [WARNING] store_checks:76 j281Ndo9 FAIL PROD_CORRELATION limit=0.7 val=0.78",
            "2026-10-05 08:39:16,087 [INFO] store_checks:92 j281Ndo9: P=13 F=1 W=5 Pend=0",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["summaries"]["j281Ndo9"] == {"pass": 13, "fail": 1, "warn": 5, "pending": 0}
    p.report("2026-10-05", data)
    out = capsys.readouterr().out
    assert "P=13 F=1 W=5 Pend=0" in out
    assert "PROD_CORRELATION" in out


def test_counts_platform_errored_batches(logdir, capsys):
    _write(
        logdir,
        "errors.log",
        [
            "2026-10-05 08:33:08,343 [ERROR] poll_batch:164 B70 done (error): "
            "simulation finished without result (status=ERROR) age=273s",
            "2026-10-05 08:33:08,832 [ERROR] poll_batch:164 B71 done (error): "
            "simulation finished without result (status=ERROR) age=272s",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["error_batches"] == 2


def test_polish_batches_are_joined_to_their_results(logdir, capsys):
    _write(logdir, "alpha.log", [ALPHA_OK])
    _write(
        logdir,
        "submit.log",
        [
            "2026-10-05 09:36:21,831 [INFO] take_batch:109 B7: polishing 2 near-miss "
            "alpha(s) in HKG/TOP800/d1 under NONE: A1, A2",
        ],
    )
    _write(
        logdir,
        "poll.log",
        [
            "2026-10-05 09:44:01,972 [INFO] fetch_alpha:29 B7 alpha NEW1: sharpe=1.71 HKG/TOP800",
            "2026-10-05 09:44:03,140 [INFO] fetch_alpha:29 B7 alpha NEW2: sharpe=-0.22 HKG/TOP800",
        ],
    )
    data = p.collect("2026-10-05")
    assert len(data["polish"]) == 1
    assert data["polish"][0]["idx"] == "7"
    assert data["polish"][0]["produced"] == [("NEW1", 1.71), ("NEW2", -0.22)]
    p.report("2026-10-05", data)
    out = capsys.readouterr().out
    assert "polish batches" in out and "NEW1(+1.71)" in out


def test_polish_line_without_a_batch_index_is_still_reported(logdir, capsys):
    """The index was added after the first batch ran; older lines still count."""
    _write(logdir, "alpha.log", [ALPHA_OK])
    _write(
        logdir,
        "submit.log",
        [
            "2026-10-05 09:36:21,831 [INFO] take_batch:109 Polishing 3 near-miss alpha(s) "
            "in HKG/TOP800/d1 under NONE: A1, A2, A3",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["polish"][0]["idx"] is None
    assert data["polish"][0]["produced"] == []
    p.report("2026-10-05", data)
    assert "no results yet" in capsys.readouterr().out


def test_a_single_expression_polish_batch_is_joined_to_its_result(logdir, capsys):
    """A polish batch is one expression, so its alpha lands on the parent.

    That path runs `runner.poll_single.handle_single`, not `fetch_alpha`, and
    `BATCH_ALPHA_RE` used to be anchored to the `fetch_alpha` logger name — so
    every polish batch reported "no results yet" for the rest of the day,
    however long ago it had finished. Measured 2026-10-09: B584 stored
    `omWawNWl` at 01:43:33 and `make progress` still showed it empty at 11:10.
    """
    _write(
        logdir,
        "alpha.log",
        [
            ALPHA_OK,
            "2026-10-05 09:44:01,972 [INFO] log_alpha:58 alpha=NEW1 sh=1.71 ts=0.64 "
            "fi=1.09 to=0.2867 rn=0.00 HKG/TOP800/d1 n=NONE",
        ],
    )
    _write(
        logdir,
        "submit.log",
        [
            "2026-10-05 09:36:21,831 [INFO] take_batch:109 B584: polishing 1 near-miss "
            "alpha(s) in HKG/TOP800/d1 under NONE: A1",
        ],
    )
    _write(
        logdir,
        "poll.log",
        [
            # The post-2026-10-09 form: the INFO line carries the sharpe.
            "2026-10-05 09:44:01,972 [INFO] handle_single:40 B584 alpha NEW1: sharpe=1.71 HKG/TOP800",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["polish"][0]["produced"] == [("NEW1", 1.71)]
    p.report("2026-10-05", data)
    assert "NEW1(+1.71)" in capsys.readouterr().out


def test_a_sharpe_less_single_line_recovers_its_sharpe_from_alpha_log(logdir, capsys):
    """Days already on disk predate that INFO line; the id still links them.

    Before 2026-10-09 `handle_single` wrote only "B584 alpha omWawNWl: HTTP
    200", which has no sharpe. alpha.log has one line per stored alpha and the
    id is the key, so the join recovers it rather than reporting the day empty.
    """
    _write(
        logdir,
        "alpha.log",
        [
            ALPHA_OK,
            "2026-10-05 01:43:33,934 [INFO] log_alpha:58 alpha=omWawNWl sh=0.09 ts=0.62 "
            "fi=0.02 to=0.2287 rn=0.38 KOR/TOP600/d1 n=SUBINDUSTRY",
        ],
    )
    # Submit before the poll: the join requires the result to postdate the
    # batch, because `batch_idx` restarts at 0 in every process and an old
    # batch's alphas would otherwise be attributed to a fresh polish batch.
    _write(
        logdir,
        "submit.log",
        [
            "2026-10-05 01:33:21,487 [INFO] take_batch:68 B584: polishing 1 near-miss "
            "alpha(s) in KOR/TOP600/d1 under SUBINDUSTRY: RR6e0MK1",
        ],
    )
    _write(
        logdir,
        "poll.log",
        ["2026-10-05 01:43:33,892 [DEBUG] handle_single:21 B584 alpha omWawNWl: HTTP 200"],
    )
    data = p.collect("2026-10-05")
    assert data["polish"][0]["produced"] == [("omWawNWl", 0.09)]


def test_a_single_batch_counts_its_alpha_once(logdir, capsys):
    """Both of that batch's lines match now, and must not count twice."""
    _write(
        logdir,
        "alpha.log",
        [
            ALPHA_OK,
            "2026-10-05 09:44:01,972 [INFO] log_alpha:58 alpha=NEW1 sh=1.71 ts=0.64 "
            "fi=1.09 to=0.2867 rn=0.00 HKG/TOP800/d1 n=NONE",
        ],
    )
    _write(
        logdir,
        "submit.log",
        [
            "2026-10-05 09:36:21,831 [INFO] take_batch:109 B584: polishing 1 near-miss "
            "alpha(s) in HKG/TOP800/d1 under NONE: A1",
        ],
    )
    _write(
        logdir,
        "poll.log",
        [
            "2026-10-05 09:44:01,970 [DEBUG] handle_single:21 B584 alpha NEW1: HTTP 200",
            "2026-10-05 09:44:01,972 [INFO] handle_single:40 B584 alpha NEW1: sharpe=1.71 HKG/TOP800",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["polish"][0]["produced"] == [("NEW1", 1.71)]


def test_report_survives_an_empty_day(logdir, capsys):
    p.report("2026-10-05", p.collect("2026-10-05"))
    assert "no alpha.log lines" in capsys.readouterr().out


def test_current_check_logger_preserves_native_failure_reasons(logdir, capsys):
    _write(logdir, "alpha.log", [ALPHA_OK])
    _write(
        logdir,
        "check.log",
        [
            "2026-10-05 10:30:02,526 [WARNING] _record_check_rows:67 "
            "j281Ndo9 FAIL CONCENTRATED_WEIGHT limit=0.1 val=1.0",
            "2026-10-05 10:30:02,628 [INFO] store_checks:80 j281Ndo9: P=13 F=1 W=5 Pend=0",
        ],
    )
    data = p.collect("2026-10-05")
    assert data["checks"]["j281Ndo9"] == [("CONCENTRATED_WEIGHT", "FAIL")]
    p.report("2026-10-05", data)
    assert "CONCENTRATED_WEIGHT" in capsys.readouterr().out
