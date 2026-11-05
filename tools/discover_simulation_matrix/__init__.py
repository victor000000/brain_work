"""Discover the canonical (region, universe, delay) matrix from BRAIN's
``OPTIONS /simulations`` endpoint — same schema the BRAIN UI uses for the sim
form. Writes a legacy-shape JSON consumed by apply_discovery_and_redownload
plus a richer canonical schema file.

CLI: `python3 -m tools.discover_simulation_matrix`
"""

from tools.discover_simulation_matrix.runner import main

__all__ = ["main"]
