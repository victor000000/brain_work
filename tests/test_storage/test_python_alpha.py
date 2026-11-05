"""Python results preserve source/settings without polluting FASTEXPR priors."""

import importlib
import json

from storage.store_alpha import store_alpha
from tests.test_storage.conftest import alpha_data, conn, settings

SOURCE = """from brain.alphas import alpha
import numpy as np
# sales is mentioned only in prose, not used as an input.
@alpha(data=["returns"], store=[])
def signal(data, store):
    return np.asarray(data.returns[-1], dtype=np.float32)
"""


def test_python_storage_is_idempotent_and_preserves_settings(monkeypatch):
    module = importlib.import_module("storage.store_alpha")
    monkeypatch.setattr(module, "_FIELD_CAT_CACHE", {"returns": "pv", "sales": "fundamental"})
    c = conn()
    # Another alpha's count must survive storing Python functions with similar names.
    store_alpha(c, "s0", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("prior"))
    payload = alpha_data("python")
    config = {**settings(), "language": "PYTHON", "lookback": 59}
    for _ in range(2):
        store_alpha(c, "s1", SOURCE, "IND", "TOP500", 1, config, payload)
    row = c.execute(
        "SELECT expression,template,pyramid_categories,raw_json FROM alpha_results WHERE alpha_id='python'"
    ).fetchone()
    assert row[:3] == (SOURCE, "python:unclassified", '["pv"]')
    assert json.loads(row[3])["_submitted_settings"] == config
    assert "_submitted_settings" not in payload
    assert c.execute("SELECT operator,count FROM operator_usage").fetchall() == [("rank", 1)]


def test_replacing_legacy_fastexpr_result_untracks_once(monkeypatch):
    module = importlib.import_module("storage.store_alpha")
    monkeypatch.setattr(module, "_FIELD_CAT_CACHE", {"returns": "pv"})
    c = conn()
    store_alpha(c, "s0", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("same"))
    for _ in range(2):
        store_alpha(c, "s1", SOURCE, "IND", "TOP500", 1, {**settings(), "language": "PYTHON"}, alpha_data("same"))
    assert c.execute("SELECT COUNT(*) FROM operator_usage").fetchone()[0] == 0
