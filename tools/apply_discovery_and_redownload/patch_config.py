"""Rewrite the canonical `REGION_CONFIGS` matrix in core/regions.py.

`download/fetch_fields.py` no longer holds a literal `REGION_CONFIG = {...}`
block — it derives its config from `core.regions.REGION_CONFIGS` — so the old
regex could never match (re.subn returned 0 and the tool exited 1). The
canonical matrix lives in core/regions.py, and that is what this patches.

The new list is compiled and re-imported from source *before* anything is
written, so a malformed render can never replace a working matrix; the previous
file is kept at `.bak` and the write is atomic.
"""

import ast
import os
import re
import sys

from tools.apply_discovery_and_redownload._config import REGIONS_PATH
from tools.apply_discovery_and_redownload._log import log
from tools.apply_discovery_and_redownload.patch_config_render import _merged, _render_list

_BLOCK_RE = re.compile(r"REGION_CONFIGS\s*=\s*\[[\s\S]*?\n\]")


def _verify(new_src, expected):
    """Parse the rendered source and check the literal; raise ValueError on mismatch."""
    tree = ast.parse(new_src, filename=REGIONS_PATH)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "REGION_CONFIGS" for t in node.targets):
            got = [(r, u, int(d)) for r, u, d in ast.literal_eval(node.value)]
            if got != expected:
                raise ValueError(f"rendered matrix does not round-trip ({len(got)} vs {len(expected)} combos)")
            return
    raise ValueError("rendered source has no REGION_CONFIGS assignment")


def patch_region_config(discovered):
    """Write the merged matrix into core/regions.py, with a .bak and a syntax check."""
    with open(REGIONS_PATH) as f:
        src = f.read()

    merged = _merged(discovered)
    rendered = _render_list(merged)
    new_src, n = _BLOCK_RE.subn(rendered, src, count=1)
    if n != 1:
        log.error(
            "No `REGION_CONFIGS = [ ... ]` block found in %s. The canonical matrix moved; "
            "patch it by hand or update this tool.",
            REGIONS_PATH,
        )
        sys.exit(1)

    try:
        _verify(new_src, merged)
    except (SyntaxError, KeyError, ValueError) as err:
        log.error("Refusing to write %s: rendered matrix failed validation (%s)", REGIONS_PATH, err)
        sys.exit(1)

    with open(REGIONS_PATH + ".bak", "w") as f:
        f.write(src)
    tmp = REGIONS_PATH + ".tmp"
    with open(tmp, "w") as f:
        f.write(new_src)
    os.replace(tmp, REGIONS_PATH)
    log.info("Patched %s (%d combos); backup at %s.bak", REGIONS_PATH, len(merged), REGIONS_PATH)
