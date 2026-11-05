"""Portfolio shape KPI — package layout.

Adapts cnhkmcp's value_factor_trendScore. Reports a 2x2 matrix of scores per
(population, atom-definition):

  Populations: hits (is_sharpe >= 1.0) and submit-attempts
               (status IN ('SUBMITTED','REJECTED','THROTTLED'))
  Atom defs:   by dataset (DATA_USAGE:SINGLE_DATA_SET classification)
               and by category (pyramid_categories.length == 1)

For each combination computes:
  S_A = atomic / N
  S_P = pyramids_covered / pyramid_multipliers_distinct_categories
  S_H = normalized Shannon entropy of per-category alpha occurrence
  score = S_A * S_P * S_H

Multi-category alphas contribute to each of their categories in the
per-pyramid distribution (matches cnhkmcp's pyramidThemes accumulation).

CLI: `python3 -m tools.portfolio_kpi`
"""

from tools.portfolio_kpi.runner import main

__all__ = ["main"]
