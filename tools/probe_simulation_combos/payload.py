"""Build a minimal /simulations request body for combo probing.

Uses the trivial expression "close" with conservative settings so the request
exercises the validation path without consuming meaningful sim budget. The
caller is expected to DELETE accepted simulations to free the slot.
"""


def build_payload(region, universe, delay):
    return {
        "type": "REGULAR",
        "settings": {
            "instrumentType": "EQUITY",
            "region": region,
            "universe": universe,
            "delay": delay,
            "decay": 0,
            "neutralization": "NONE",
            "truncation": 0.08,
            "pasteurization": "ON",
            "unitHandling": "VERIFY",
            "nanHandling": "OFF",
            "language": "FASTEXPR",
            "visualization": False,
            "testPeriod": "P0Y0M",
            "maxTrade": "OFF",
        },
        "regular": "close",
    }
