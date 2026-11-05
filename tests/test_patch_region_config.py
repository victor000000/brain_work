"""patch_config must patch the canonical matrix, and only when it can do so safely.

`download/fetch_fields.py` derives its REGION_CONFIG from
`core.regions.REGION_CONFIGS`, so the old literal-block regex could never match
and the tool always exited 1. These tests run the patch against a copy.
"""

import ast
import os

import pytest

from core.regions import REGION_CONFIGS
from tools.apply_discovery_and_redownload import patch_config


@pytest.fixture
def regions_copy(tmp_path, monkeypatch):
    """A copy of the real core/regions.py, with the tool pointed at it."""
    from tools.apply_discovery_and_redownload._config import PROJECT_DIR

    src_path = tmp_path / "regions.py"
    with open(os.path.join(PROJECT_DIR, "core", "regions.py")) as fh:
        src_path.write_text(fh.read())
    monkeypatch.setattr(patch_config, "REGIONS_PATH", str(src_path))
    return src_path


def _combos(path):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "REGION_CONFIGS" for t in node.targets):
            return [tuple(int(x) if isinstance(x, int) else x for x in row) for row in ast.literal_eval(node.value)]
    raise AssertionError("no REGION_CONFIGS in patched file")


def test_new_combos_are_appended(regions_copy):
    before = _combos(regions_copy)
    assert ("USA", "TOP3000", 2) not in before
    patch_config.patch_region_config({"USA": {"universes": {"TOP3000"}, "delays": {2}}})
    after = _combos(regions_copy)
    assert after[: len(before)] == before
    assert after[len(before) :] == [("USA", "TOP3000", 2)]


def test_existing_combos_are_preserved(regions_copy):
    patch_config.patch_region_config({"JPN": {"universes": {"TOP500"}, "delays": {1}}})
    assert set(REGION_CONFIGS) <= set(_combos(regions_copy))


def test_backup_holds_the_original(regions_copy):
    original = regions_copy.read_text()
    patch_config.patch_region_config({"JPN": {"universes": {"TOP500"}, "delays": {1}}})
    assert (regions_copy.parent / "regions.py.bak").read_text() == original


def test_patched_file_is_valid_python(regions_copy):
    patch_config.patch_region_config({"JPN": {"universes": {"TOP500"}, "delays": {1}}})
    ast.parse(regions_copy.read_text())  # raises SyntaxError on a bad render


def test_no_duplicate_combos(regions_copy):
    patch_config.patch_region_config({"USA": {"universes": {"TOP3000"}, "delays": {1, 0}}})
    combos = _combos(regions_copy)
    assert len(combos) == len(set(combos))


def test_delay_values_are_integers(regions_copy):
    patch_config.patch_region_config({"JPN": {"universes": {"TOP500"}, "delays": {"1"}}})
    assert ("JPN", "TOP500", 1) in _combos(regions_copy)


def test_missing_block_exits_with_a_clear_message(tmp_path, monkeypatch, caplog):
    """A file without the block must fail loudly, not silently do nothing."""
    path = tmp_path / "regions.py"
    path.write_text("SOMETHING_ELSE = 1\n")
    monkeypatch.setattr(patch_config, "REGIONS_PATH", str(path))

    with pytest.raises(SystemExit) as exc:
        patch_config.patch_region_config({"JPN": {"universes": {"TOP500"}, "delays": {1}}})
    assert exc.value.code == 1
    assert path.read_text() == "SOMETHING_ELSE = 1\n"
    assert "The canonical matrix moved" in caplog.text
