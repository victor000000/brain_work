"""P4 portfolio shape KPI — pure helpers.

Imported by `tools/portfolio_kpi.py`. Split out so tests skip the script's
DB-and-print glue layer. No I/O, no DB.

normalized_entropy: Shannon entropy in bits, normalized to [0, 1] by log2(P)
is_atom_by_dataset: detects BRAIN's DATA_USAGE:SINGLE_DATA_SET classification
"""

import math


def normalized_entropy(counts: dict[str, int]) -> float:
    """Shannon entropy in bits, normalized to [0, 1] by log2(P).

    P = number of distinct keys with non-zero count. For P <= 1 (degenerate
    distribution) returns 0.0. Empty dict returns 0.0.
    """
    if not counts:
        return 0.0
    total = sum(counts.values())
    if total == 0:
        return 0.0
    p = sum(1 for c in counts.values() if c > 0)
    if p <= 1:
        return 0.0
    h = -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)
    return h / math.log2(p)


def is_atom_by_dataset(raw_json: dict) -> bool:
    """True iff the alpha's classifications include DATA_USAGE:SINGLE_DATA_SET.

    Defensive against missing or None classifications field — both treated as
    non-atomic.
    """
    cls = raw_json.get("classifications") or []
    return any(c.get("id") == "DATA_USAGE:SINGLE_DATA_SET" for c in cls)
