"""Position/trade constraints learned from BRAIN error responses."""

# maxPosition not available in these regions (from error logs).
#
# AMR, DEU and GBR were added to REGION_CONFIGS on 2026-10-09 without an entry
# here, so `_pick_trade_position` sent `maxPosition=ON` on a quarter of their
# fills and the platform answered
# `HTTP 400 [{"settings":{"maxPosition":["Max Position is not available for
# region AMR"]}}]` — 25 batches on 2026-10-09 and 1 on 2026-10-10, each burning
# a full 10-expression generation cycle plus a POST. The platform names the
# region in the message, which is this map's source.
NO_MAX_POSITION_REGIONS = {
    "HKG",
    "GLB",
    "KOR",
    "IND",
    "ASI",
    "CHN",
    "JPN",
    "TWN",
    "MEA",
    "AMR",
    "DEU",
    "GBR",
}

# maxTrade and maxPosition cannot both be ON (per BRAIN error log).
MAX_TRADE_POSITION_CONFLICT = True
