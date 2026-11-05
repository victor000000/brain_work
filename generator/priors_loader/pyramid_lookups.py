"""Pyramid-multiplier lookups used by the priors recompute."""

from generator.priors_loader._constants import _SATURATION_CAP_N


def load_pyramid_lookups(conn):
    """Return (mults, counts) — latest snapshots keyed by (category, region, delay).

    Both tables share a `fetched_at` invariant in download.pyramid: latest
    multiplier and latest alpha_count snapshots come from the same refresh.
    Empty when no snapshot exists yet — caller defaults expected_multiplier
    to 1.0 in that case.
    """
    mults = {
        (c, r, d): m
        for c, r, d, m in conn.execute(
            "SELECT category, region, delay, multiplier FROM pyramid_multipliers "
            "WHERE fetched_at = (SELECT MAX(fetched_at) FROM pyramid_multipliers)"
        )
    }
    counts = {
        (c, r, d): n
        for c, r, d, n in conn.execute(
            "SELECT category, region, delay, alpha_count FROM pyramid_alpha_counts "
            "WHERE fetched_at = (SELECT MAX(fetched_at) FROM pyramid_alpha_counts)"
        )
    }
    return mults, counts


def alpha_max_multiplier(cats, region, delay, mults, counts):
    """Cap-adjusted max multiplier across an alpha's categories.

    For each category in cats:
      - look up multiplier(cat, region, delay)
      - look up alpha_count(cat, region, delay) (default 0)
      - if alpha_count > _SATURATION_CAP_N, clip multiplier to 1.0
    Return max of the adjusted values, or None if no category resolved.
    """
    adj = []
    for c in cats:
        m = mults.get((c, region, delay))
        if m is None:
            continue
        n = counts.get((c, region, delay), 0)
        adj.append(1.0 if n > _SATURATION_CAP_N else m)
    return max(adj) if adj else None
