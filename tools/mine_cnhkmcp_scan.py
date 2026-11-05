"""Walk candidate files and keep the expressions py-fastplus accepts.

Split out of `tools/mine_cnhkmcp_templates.py`, which re-exports these names.
"""

import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import fastplus  # noqa: E402

from tools.mine_cnhkmcp_ref import _read  # noqa: E402


def walk_strings(obj, path):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")


def strings_from(fp, rel):
    """Text blobs to scan from one file; empty when it cannot be decoded."""
    try:
        if fp.endswith(".json"):
            return [s for _p, s in walk_strings(json.loads(_read(fp)), rel)]
        return [_read(fp)]
    except Exception:
        return []


def parses(expr):
    """True when py-fastplus accepts the candidate — most candidates fail."""
    try:
        fastplus.parse(expr)
        return True
    except Exception:
        return False
