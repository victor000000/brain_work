# Platform Constraints (from API OPTIONS + error logs)

## Region-Specific Neutralization
STATISTICAL NOT available: CHN, HKG, IND, KOR

## Region-Specific Settings
maxPosition NOT available: HKG, GLB, KOR, IND, ASI
maxTrade + maxPosition: cannot both be ON

## Simulation Errors (common)
- "Incompatible unit" — mixing price/ratio in add/subtract
- "Expression ends with group unit value" — group op not wrapped in rank()
- "Neutralization X not available for region Y"
- "Max Position not available for region X"
- "Operator X does not support event inputs" — VECTOR field in wrong op
- "Data field X not available in universe Y" — field varies by universe

## Submission Checks (hardest to pass)
1. IS_LADDER_SHARPE — 98% fail (need time-stable performance)
2. LOW_SHARPE — 96% fail (thresholds vary: EUR/d1~1.58, CHN/d1~2.07)
3. LOW_FITNESS — 93% fail (need >= 1.0)
