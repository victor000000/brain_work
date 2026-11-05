"""Probe BRAIN's /simulations endpoint to classify each (region, universe, delay)
combo as accepted, rejected, or other-error.

Useful when REGION_CONFIGS is expanded — /data-fields exposing a combo does
not guarantee /simulations accepts it (e.g. EUR/TOP500).

CLI: `python3 -m tools.probe_simulation_combos`
"""

from tools.probe_simulation_combos.classify import classify
from tools.probe_simulation_combos.probe import probe_combo
from tools.probe_simulation_combos.runner import main

__all__ = ["classify", "main", "probe_combo"]
