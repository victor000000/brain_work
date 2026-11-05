"""Top-level orchestration for `python3 -m tools.apply_discovery_and_redownload`."""

import subprocess
import sys

from download.session import BrainSession
from tools.apply_discovery_and_redownload._config import PROJECT_DIR
from tools.apply_discovery_and_redownload._log import log
from tools.apply_discovery_and_redownload.clear_log import clear_stale_download_log
from tools.apply_discovery_and_redownload.diff import new_combos_vs_region_config
from tools.apply_discovery_and_redownload.discovery_io import load_discovery
from tools.apply_discovery_and_redownload.grown_subcats import grown_subcats
from tools.apply_discovery_and_redownload.patch_config import patch_region_config


def _summarize_discovery(discovered):
    n_combos = sum(len(v["universes"]) * len(v["delays"]) for v in discovered.values())
    log.info("Discovery: %d regions, %d combos total", len(discovered), n_combos)


def _summarize_new_combos(new_combos):
    log.info("New combos vs REGION_CONFIG: %d", len(new_combos))
    for c in new_combos:
        log.info("  + %s/%s/d%d", *c)


def _run_brain_data_subprocess():
    """Run brain_data as a fresh subprocess so it sees the patched config and
    sets up its own logger handlers without colliding with ours."""
    log.info("-" * 60)
    log.info("Launching download.brain_data subprocess")
    log.info("-" * 60)
    rc = subprocess.call([sys.executable, "-m", "download.brain_data"], cwd=PROJECT_DIR)
    log.info("download.brain_data exited with rc=%d", rc)
    return rc


def main():
    log.info("=" * 60)
    log.info("apply_discovery_and_redownload")
    log.info("=" * 60)

    discovered = load_discovery()
    _summarize_discovery(discovered)

    new_combos = new_combos_vs_region_config(discovered)
    _summarize_new_combos(new_combos)

    if new_combos:
        patch_region_config(discovered)

    brain = BrainSession()
    brain.authenticate()

    grown = grown_subcats(brain)
    log.info("Grown subcategories: %d", len(grown))
    for sid in grown:
        log.info("  grown: %s", sid)

    clear_stale_download_log(grown, new_combos)
    sys.exit(_run_brain_data_subprocess())
