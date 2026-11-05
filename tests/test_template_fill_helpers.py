"""Field and operator pools shared by the template-fill tests."""

FIELDS = ["close", "volume", "returns", "cap", "vwap", "adv20"]
OPS = {
    "rank",
    "zscore",
    "ts_backfill",
    "ts_rank",
    "ts_delta",
    "max",
    "group_rank",
    "group_neutralize",
    "group_mean",
    "vec_avg",
}
