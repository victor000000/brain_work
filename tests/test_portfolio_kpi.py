"""Tests for P4 portfolio shape KPI — pure helpers."""


def test_normalized_entropy_uniform_two_bins():
    """50/50 split across 2 bins -> S_H = 1.0 (maximum normalized entropy)."""
    from tools._kpi_helpers import normalized_entropy

    assert normalized_entropy({"a": 50, "b": 50}) == 1.0


def test_normalized_entropy_concentrated_single_bin():
    """All occurrences in one bin -> P=1 -> S_H = 0.0 (degenerate distribution)."""
    from tools._kpi_helpers import normalized_entropy

    assert normalized_entropy({"a": 100}) == 0.0


def test_normalized_entropy_uniform_three_bins():
    """Approximately uniform across 3 bins -> S_H ~= 1.0."""
    from tools._kpi_helpers import normalized_entropy

    assert abs(normalized_entropy({"a": 33, "b": 33, "c": 34}) - 1.0) < 1e-3


def test_normalized_entropy_empty_dict_returns_zero():
    """Empty dict -> 0.0 (no division by zero)."""
    from tools._kpi_helpers import normalized_entropy

    assert normalized_entropy({}) == 0.0


def test_is_atom_by_dataset_detects_classification():
    """raw_json.classifications including DATA_USAGE:SINGLE_DATA_SET -> True; otherwise False."""
    from tools._kpi_helpers import is_atom_by_dataset

    rj_atom = {
        "classifications": [
            {"id": "DATA_USAGE:SINGLE_DATA_SET", "name": "Single Data Set Alpha"},
        ]
    }
    rj_non_atom = {
        "classifications": [
            {"id": "HIGH_TURNOVER:HIGH_TURNOVER", "name": "High Turnover"},
        ]
    }
    rj_empty = {"classifications": []}
    rj_missing = {}
    rj_none_classifications = {"classifications": None}

    assert is_atom_by_dataset(rj_atom) is True
    assert is_atom_by_dataset(rj_non_atom) is False
    assert is_atom_by_dataset(rj_empty) is False
    assert is_atom_by_dataset(rj_missing) is False
    assert is_atom_by_dataset(rj_none_classifications) is False
