"""Top-level runner for `python3 -m tools.probe_simulation_combos`."""

import argparse
import time

# Imported here so the package's _config sys.path injection runs first.
from core.auth import get_session
from tools.probe_simulation_combos._config import THROTTLE_SECONDS
from tools.probe_simulation_combos._log import log
from tools.probe_simulation_combos.load_combos import load_combos
from tools.probe_simulation_combos.persist import dump_results
from tools.probe_simulation_combos.probe import probe_combo
from tools.probe_simulation_combos.report import report_rejects, report_summary


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discovery", action="store_true", help="Probe combos from discover_universes.json")
    ap.add_argument("--combos", nargs="*", help="Specific combos as REGION/UNIVERSE/DELAY")
    return ap.parse_args()


def main():
    args = _parse_args()
    combos = load_combos(args)

    log.info("=" * 60)
    log.info("Probing %d (region, universe, delay) combos", len(combos))
    log.info("=" * 60)

    session = get_session()
    results = []
    for region, universe, delay in combos:
        verdict, detail = probe_combo(session, region, universe, delay)
        log.info("[%-20s] %s/%s/d%d %s", verdict, region, universe, delay, detail[:120])
        results.append(
            {
                "region": region,
                "universe": universe,
                "delay": delay,
                "verdict": verdict,
                "detail": detail,
            }
        )
        time.sleep(THROTTLE_SECONDS)

    dump_results(results)
    report_summary(results)
    report_rejects(results)
