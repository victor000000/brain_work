"""Locate the active interpreter's shared library for native parser tests."""

import sys
import sysconfig
from pathlib import Path


def library_dir():
    library = sysconfig.get_config_var("LDLIBRARY")
    if not library:
        raise RuntimeError("Python does not expose a shared library name")
    # Relocated standalone Python builds may retain their build host's LIBDIR.
    candidates = [Path(sys.base_prefix) / "lib"]
    configured = sysconfig.get_config_var("LIBDIR")
    if configured:
        candidates.append(Path(configured))
    for candidate in candidates:
        try:
            if (candidate / library).is_file():
                return str(candidate)
        except OSError:
            continue
    raise RuntimeError(f"Cannot find Python shared library {library} for native tests")


if __name__ == "__main__":
    print(library_dir())
