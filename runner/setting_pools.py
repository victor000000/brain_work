"""All possible values for simulation settings.

Tuned based on cnhkmcp analysis:
- Pasteurization: always ON (in settings_factory)
- Truncation: 0.08 standard (cnhkmcp default)
- Decay: 4-10 for turnover control (cnhkmcp default=4)
- Test period: shorter for IS_LADDER_SHARPE consistency
"""

NEUTRALIZATIONS = [
    "MARKET",
    "SECTOR",
    "INDUSTRY",
    "SUBINDUSTRY",
    "NONE",
    "SLOW_AND_FAST",
    "SLOW",
    "FAST",
    "CROWDING",
    "REVERSION_AND_MOMENTUM",
    "STATISTICAL",
]

# cnhkmcp default decay=4. Higher = less turnover
DECAYS = [3, 4, 5, 5, 8, 8, 10, 10, 15]

# cnhkmcp standard: 0.08
TRUNCATIONS = [0.05, 0.08, 0.08, 0.08, 0.10]

# Shorter test periods improve IS_LADDER_SHARPE
TEST_PERIODS = ["P0Y6M", "P0Y6M", "P1Y0M", "P1Y0M", "P1Y6M"]
