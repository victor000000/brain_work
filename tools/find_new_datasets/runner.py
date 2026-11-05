"""Top-level runner for `python3 -m tools.find_new_datasets`."""

import argparse

from download.session import BrainSession
from tools.find_new_datasets._log import log
from tools.find_new_datasets.api import fetch_subcategories
from tools.find_new_datasets.diff import grew_subcats
from tools.find_new_datasets.local_state import load_local_state
from tools.find_new_datasets.report import report_findings, report_flagged
from tools.find_new_datasets.scan import scan_subcat_for_new


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-subcats", action="store_true", help="Scan every subcategory regardless of cached-count diff")
    return ap.parse_args()


def main():
    args = _parse_args()

    log.info("=" * 60)
    log.info("BRAIN new-dataset finder")
    log.info("=" * 60)

    brain = BrainSession()
    brain.authenticate()

    known_ids, cached_counts = load_local_state()
    log.info("Local: %d distinct datasets across %d subcategories", len(known_ids), len(cached_counts))

    api_subcats = fetch_subcategories(brain)
    log.info("BRAIN: %d subcategories", len(api_subcats))

    flagged = grew_subcats(api_subcats, cached_counts, args.all_subcats)
    if not flagged:
        log.info("No subcategory growth detected (cached datasetCount matches API).")
        log.info("Use --all-subcats to force a full page-1 scan anyway.")
        return

    report_flagged(flagged, cached_counts)

    found, total_calls = {}, 0
    for sid, _name, _old, _new, _delta in flagged:
        log.info("Scanning %s ...", sid)
        total_calls += scan_subcat_for_new(brain, sid, known_ids, found)

    report_findings(found, total_calls)
