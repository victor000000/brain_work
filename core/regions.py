"""Canonical (region, universe, delay) matrix from BRAIN's OPTIONS /simulations.

Refresh by running `python3 -m tools.discover_simulation_matrix`, which queries
BRAIN's OPTIONS /simulations endpoint (the same schema the BRAIN UI uses) and
writes the result to brain_logs/discover_simulation_matrix.full.json. Then
mirror that into REGION_CONFIGS below.
"""

REGION_CONFIGS = [
    # USA: 7 universes, delays 0 and 1
    ("USA", "TOP3000", 1),
    ("USA", "TOP3000", 0),
    ("USA", "TOP2000", 1),
    ("USA", "TOP2000", 0),
    ("USA", "TOP1000", 1),
    ("USA", "TOP1000", 0),
    ("USA", "TOP500", 1),
    ("USA", "TOP500", 0),
    ("USA", "TOP200", 1),
    ("USA", "TOP200", 0),
    ("USA", "TOPSP500", 1),
    ("USA", "TOPSP500", 0),
    # EUR: 6 universes, delays 0 and 1
    ("EUR", "TOP2500", 1),
    ("EUR", "TOP2500", 0),
    ("EUR", "TOP1200", 1),
    ("EUR", "TOP1200", 0),
    ("EUR", "TOP800", 1),
    ("EUR", "TOP800", 0),
    ("EUR", "TOP400", 1),
    ("EUR", "TOP400", 0),
    ("EUR", "TOPCS1600", 1),
    ("EUR", "TOPCS1600", 0),
    # GLB: 4 universes, delay 1
    ("GLB", "TOP3000", 1),
    ("GLB", "MINVOL1M", 1),
    ("GLB", "MINVOL10M", 1),
    ("GLB", "TOPDIV3000", 1),
    # ASI: 3 universes, delay 1
    ("ASI", "MINVOL1M", 1),
    ("ASI", "MINVOL10M", 1),
    ("ASI", "TOP500", 1),
    # CHN: 1 universe, delays 0 and 1
    ("CHN", "TOP2000U", 1),
    ("CHN", "TOP2000U", 0),
    # KOR, HKG, IND: delay 1
    ("KOR", "TOP600", 1),
    ("HKG", "TOP800", 1),
    ("HKG", "TOP500", 1),
    ("IND", "TOP500", 1),
    # AMR, DEU, GBR: added 2026-10-09. These were previously excluded on the
    # grounds that "the local pv/option field corpus was downloaded per
    # configured region, so those regions have no fields to build expressions
    # from" — which was true, and was a reason to download the fields, not a
    # reason to stay out.
    #
    # The cost of the omission is visible in the platform's own pyramid
    # multipliers: the only two pv/option pyramids on offer on 2026-10-09 are
    # AMR/delay-0 (x1.50) and AMR/delay-1 (x1.40), both with alphaCount 0 —
    # and neither was reachable, because `pyramid3_targets._eligible_rows`
    # drops any target its cell's field pool cannot satisfy. A 1.4-1.5x
    # multiplier was scored and discarded on every refresh.
    ("AMR", "TOP600", 1),
    ("AMR", "TOP600", 0),
    ("DEU", "TOP500", 1),
    ("GBR", "TOP700", 1),
    # DEU/TOP500/d0 and GBR/TOP700/d0 are absent: the platform serves their
    # fields but reports `coverage: 0.0` on every one of them — DEU stores 126
    # MATRIX rows and GBR 122, `close` and `adv20` among them, and not one
    # clears the `coverage >= 0.5` filter `field_queries_matrix` applies. The
    # same regions at delay 1 report 1.0. So `generate_expressions` returns
    # nothing for those two cells and `tests/test_generator.py::
    # test_generate_all_regions` fails on them; the picker would have offered
    # them 2/41 of the time and produced an empty batch every time.
    #
    # Whether that 0.0 is a real property of delay-0 in those regions or a
    # metadata quirk of the data-fields response is not settled — if it is the
    # latter, these two belong back once a refresh or a probe shows otherwise.
]
# VERIFIED 2026-10-03 against a live OPTIONS /simulations response
# (brain_logs/discover_simulation_matrix.full.json, 44 combos). The harvested
# docs disagreed with each other and with the platform; the platform wins.
#
# Six combos were removed because the platform rejects them with HTTP 400 —
# every pick burned a full generation cycle plus a POST:
#   USA/ILLIQUID_MINVOL1M d0+d1, EUR/ILLIQUID_MINVOL1M d0+d1,
#   ASI/ILLIQUID_MINVOL1M d1, and MEA/TOP300 d1 (no MEA region at all).
# Sixty such rejections were logged today, 32 of them ILLIQUID_MINVOL1M.
#
# ALL is deliberately absent, and this is the case `probe_simulation_combos`
# exists to catch. ALL/LARGE, ALL/MEDIUM and ALL/SMALL are in the platform's
# OPTIONS /simulations matrix, and `GET /data-fields` answers for them — the
# 2026-10-09 refresh downloaded 4,078 pv/option field rows for each, HTTP 200
# throughout. `POST /simulations` then rejects all three:
#
#   Region ALL is not available for simulation type REGULAR.
#
# Three of nine combos added that day, dead on arrival, at three fields per
# field-count probe and a full generation cycle plus a POST each time the
# picker offered one. The fields stay in `data_fields` — harmless, since
# `_available_categories` only ever looks up configs this list contains — but
# do not re-add ALL on the strength of a field download.
#
# `download/fetch_fields.REGION_CONFIG`, derived from this list, follows it.
# The order matters to nothing but readability: the picker weights by pyramid
# score and cell yield, not by position.
