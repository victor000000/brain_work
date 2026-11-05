"""Load the reachability reference the classifier tests field names against.

Split out of `tools/parse_cnhkmcp_templates.py`, which re-exports these names.

Field reachability reference. The DB was pruned to pv/option rows, so it holds
every reachable field and dataset — membership is a positive test. Anything
else carrying a dataset prefix (`mdl216_*`, `anl14_*`) is outside the
restriction. Unprefixed foreign names cannot be resolved and are skipped
rather than assumed fillable.
"""

import json
import os

from core.db import connect_for_reading
from tools.parse_cnhkmcp_vocab import REFERENCE


def load_reference(db):
    """(reachable datafields, pv/option dataset ids) from the pruned DB."""
    conn = connect_for_reading(db)
    reachable_fields = {r[0] for r in conn.execute("SELECT id FROM data_fields")}
    pv_option_datasets = {r[0] for r in conn.execute("SELECT id FROM datasets WHERE category_id IN ('pv','option')")}
    conn.close()
    return reachable_fields, pv_option_datasets


def load_known_non_pv():
    """Foreign fields the pre-prune classification already attributed."""
    known_non_pv = set()
    if os.path.exists(REFERENCE):
        with open(REFERENCE) as fh:
            known_non_pv = set(json.load(fh).get("non_pv_fields", []))
    return known_non_pv
