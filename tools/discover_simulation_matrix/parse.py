"""Parse the OPTIONS /simulations schema into per-region universe/delay maps."""


def parse_matrix(schema):
    """Return (universe_by_region, delay_by_region).

    Both are dict[region] -> list[value] taken from the choices.instrumentType.EQUITY.region
    nested structure that BRAIN exposes.
    """
    settings = schema["actions"]["POST"]["settings"]["children"]
    universe_by_region = {
        r: [c["value"] for c in choices]
        for r, choices in settings["universe"]["choices"]["instrumentType"]["EQUITY"]["region"].items()
    }
    delay_by_region = {
        r: [c["value"] for c in choices]
        for r, choices in settings["delay"]["choices"]["instrumentType"]["EQUITY"]["region"].items()
    }
    return universe_by_region, delay_by_region
