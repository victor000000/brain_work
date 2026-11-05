"""Forum-mined template pool: mix selection and load-time filtering."""

import json

import pytest

from generator import template_source as ts
from tests import test_template_source_helpers as helpers
from tests.test_template_source_helpers import FIELDS, OPS, _clear_pool  # noqa: F401

# Bound here rather than imported by name: a direct import of `corpus` would be
# shadowed by the test parameters of the same name (ruff F811).
corpus = helpers.corpus


def test_mix_defaults_to_a_quarter():
    assert ts.template_mix() == ts.DEFAULT_MIX


def test_mix_reads_the_environment(monkeypatch):
    monkeypatch.setenv("BRAIN_TEMPLATE_MIX", "0.5")
    assert ts.template_mix() == pytest.approx(0.5)


def test_mix_clamps_and_survives_garbage(monkeypatch):
    monkeypatch.setenv("BRAIN_TEMPLATE_MIX", "9")
    assert ts.template_mix() == 1.0
    monkeypatch.setenv("BRAIN_TEMPLATE_MIX", "abc")
    assert ts.template_mix() == ts.DEFAULT_MIX


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_mix_rejects_nonfinite_probabilities(value, monkeypatch):
    monkeypatch.setenv("BRAIN_TEMPLATE_MIX", value)
    assert ts.template_mix() == ts.DEFAULT_MIX


def test_load_pool_excludes_non_pv_option_rows(corpus):
    pool = ts.load_pool(FIELDS, OPS, corpus)
    assert all(r["fillable_from_pv_option"] for r in pool)
    # The pv/option rows minus the unbalanced one, which the load-time shape
    # parse rejects: it could never produce a valid expression, so keeping it
    # only bought a wasted fill + parse per draw.
    assert [r["skeleton"] for r in pool] == ["ts_rank({f},20)", "rank(close)"]


def test_load_pool_rejects_invented_operators(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(
        json.dumps(
            [
                {"skeleton": "made_up_op({f})", "fillable_from_pv_option": True},
                {"skeleton": "rank({f})", "fillable_from_pv_option": True},
            ]
        )
    )
    pool = ts.load_pool(FIELDS, OPS, str(path))
    assert [r["skeleton"] for r in pool] == ["rank({f})"]


def test_pool_cleans_prose_and_assignment_forms_and_dedupes(tmp_path):
    """Prose and assignment variants of one expression collapse to one skeleton."""
    path = tmp_path / "t.json"
    path.write_text(
        json.dumps(
            [
                {"skeleton": "排序：rank({f}) 排名。", "fillable_from_pv_option": True},  # noqa: RUF001
                {"skeleton": "变量 = rank({f})", "fillable_from_pv_option": True},
                {"skeleton": "rank({f})", "fillable_from_pv_option": True},
            ]
        )
    )
    pool = ts.load_pool(FIELDS, OPS, str(path))
    assert [r["skeleton"] for r in pool] == ["rank({f})"]


def test_load_pool_missing_file_is_empty_not_an_error(tmp_path):
    assert ts.load_pool(FIELDS, OPS, str(tmp_path / "nope.json")) == []


def test_load_pool_labels_the_shipped_corpora():
    """The shipped corpora map to stable labels; other files fall back to stem."""
    assert ts._corpus_label("docs/forum/forum_templates.json") == "forum"
    assert ts._corpus_label("docs/forum/cnhkmcp_mined_templates.json") == "cnhkmcp"
    assert ts._corpus_label("docs/forum/cnhkmcp_curated_templates.json") == "curated"
    assert ts._corpus_label("/tmp/some_mine.json") == "some_mine"
