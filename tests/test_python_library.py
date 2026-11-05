"""Native test linking must follow a relocated interpreter's real prefix."""

import pytest

from tools import python_library


def test_relocated_prefix_takes_precedence_over_stale_libdir(tmp_path, monkeypatch):
    active = tmp_path / "python" / "lib"
    active.mkdir(parents=True)
    (active / "libpython3.12.so").touch()
    monkeypatch.setattr(python_library.sys, "base_prefix", str(active.parent))
    monkeypatch.setattr(
        python_library.sysconfig, "get_config_var", lambda key: "libpython3.12.so" if key == "LDLIBRARY" else "/missing"
    )
    assert python_library.library_dir() == str(active)


def test_missing_library_reports_the_native_build_requirement(tmp_path, monkeypatch):
    monkeypatch.setattr(python_library.sys, "base_prefix", str(tmp_path))
    monkeypatch.setattr(
        python_library.sysconfig, "get_config_var", lambda key: "libpython3.12.so" if key == "LDLIBRARY" else None
    )
    with pytest.raises(RuntimeError, match="Cannot find Python shared library"):
        python_library.library_dir()
