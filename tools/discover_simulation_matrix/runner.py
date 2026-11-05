"""Top-level runner for `python3 -m tools.discover_simulation_matrix`."""

from core.auth import get_session
from tools.discover_simulation_matrix._log import log
from tools.discover_simulation_matrix.fetch import fetch_schema
from tools.discover_simulation_matrix.parse import parse_matrix
from tools.discover_simulation_matrix.persist import write_outputs


def main():
    log.info("=" * 60)
    log.info("BRAIN simulation matrix discovery (OPTIONS /simulations)")
    log.info("=" * 60)

    session = get_session()
    schema = fetch_schema(session)
    universe_by_region, delay_by_region = parse_matrix(schema)
    full_combos = write_outputs(universe_by_region, delay_by_region)

    log.info("-" * 60)
    log.info("Per-region:")
    for region in sorted(universe_by_region):
        log.info("  %s: universes=%s delays=%s", region, universe_by_region[region], delay_by_region.get(region, []))
    log.info(
        "Total: %d (region, universe, delay) combos across %d regions",
        len(full_combos),
        len(universe_by_region),
    )
