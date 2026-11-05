"""Price/volume hypotheses for bounded probes before registry admission.

These are new hypotheses, with no claimed acceptance record. Both use one
price series and one raw-volume series from the supplied pv/option pool.
Ratios use each field's own history so operands remain dimensionless even
when the two fields come from different datasets.
"""

from generator.templates_brain_website_pick import _RAW_VOLUME_EXCLUDE, _pick_price, _pick_tokens


def return_volume_correlation(fields, rng):
    """Fade names whose daily returns rise with unusually heavy participation.

    Correlates returns, rather than price levels, with volume relative to its
    own recent mean. This differs from the registry's covariance of ranked
    price and ranked volume. The hypothesis is temporary demand pressure.
    """
    price = _pick_price(fields, rng, "close", "vwap")
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if price is None or volume is None:
        return None
    window = rng.choice((20, 40, 60))
    returns = f"ts_delta({price}, 1) / ts_delay({price}, 1)"
    activity = f"{volume} / ts_mean({volume}, 20)"
    return f"-rank(ts_corr({returns}, {activity}, {window}))"


def activity_weighted_reversal(fields, rng):
    """Fade a short price move most strongly when participation is exceptional.

    A ranked activity ratio adjusts a ranked return signal continuously,
    instead of the registry's binary volume gate. Both legs are unitless;
    the price change is divided by its own starting price.
    """
    price = _pick_price(fields, rng, "close", "vwap")
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if price is None or volume is None:
        return None
    window = rng.choice((3, 5, 10))
    returns = f"ts_delta({price}, {window}) / ts_delay({price}, {window})"
    activity = f"{volume} / ts_mean({volume}, 20)"
    return f"-rank({returns}) * rank({activity})"


IDEA_TEMPLATES = (return_volume_correlation, activity_weighted_reversal)
