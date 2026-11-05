"""Regions whose OPTIONS /simulations exposes STATISTICAL neutralization."""

# These four regions accept the full 12-value neutralization set.
NEUT_WITH_STATISTICAL = {
    "ASI": {
        "COUNTRY",
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    "EUR": {
        "COUNTRY",
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    "GLB": {
        "COUNTRY",
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    "USA": {
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    # Added 2026-10-10. These three regions went into REGION_CONFIGS on
    # 2026-10-09 for the AMR pyramid multiplier but were never added here, and
    # the cost was not just a narrower pool: `pick_neutralization` logs an ERROR
    # for an unknown region and falls back to the five-value cross-region
    # intersection, so every AMR/DEU/GBR batch — 122 logged picks — silently
    # drew from {INDUSTRY, MARKET, NONE, SECTOR, SUBINDUSTRY} instead of the
    # region's real set, and buried a genuine misconfiguration in per-batch
    # noise. Read from OPTIONS /simulations on 2026-10-10, the same source the
    # rest of this map cites; the endpoint reports 12 regions against the 9
    # this map held.
    #
    # AMR is the narrow one: no REVERSION_AND_MOMENTUM, CROWDING, FAST or SLOW.
    "AMR": {
        "COUNTRY",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "SECTOR",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    "DEU": {
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
    "GBR": {
        "CROWDING",
        "FAST",
        "INDUSTRY",
        "MARKET",
        "NONE",
        "REVERSION_AND_MOMENTUM",
        "SECTOR",
        "SLOW",
        "SLOW_AND_FAST",
        "STATISTICAL",
        "SUBINDUSTRY",
    },
}
