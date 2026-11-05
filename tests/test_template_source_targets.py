"""Forum-mined template pool: pyramid target-field draws."""

import json
import random

from generator import template_source as ts
from tests.test_template_source_helpers import FIELDS, OPS, _clear_pool  # noqa: F401


def test_target_fields_skip_slotless_skeletons(tmp_path):
    """A slotless skeleton cannot carry the pyramid target, so it is skipped
    rather than spending the batch's template share on an untargeted alpha."""
    path = tmp_path / "t.json"
    path.write_text(
        json.dumps(
            [
                {"skeleton": "rank(close)", "fillable_from_pv_option": True},
                {"skeleton": "ts_rank({f},20)", "fillable_from_pv_option": True},
            ]
        )
    )
    rng = random.Random(11)
    # The slotless skeleton is filtered out, so every draw must come out of the
    # slot-carrying one with the target in it — never None, never untargeted.
    exprs = [ts.next_expression(FIELDS, rng, OPS, str(path), target_fields=["cap"]) for _ in range(20)]
    assert all(expr is not None and "cap" in expr for expr in exprs), exprs


def test_target_fields_with_only_slotless_pool_returns_none(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps([{"skeleton": "rank(close)", "fillable_from_pv_option": True}]))
    assert ts.next_expression(FIELDS, random.Random(1), OPS, str(path), target_fields=["cap"]) is None
