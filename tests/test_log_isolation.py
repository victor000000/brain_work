"""Regression guard: test runs must not write the project's brain_logs/.

The root conftest redirects `core.log_config.LOG_DIR` into the session
sandbox before anything else is imported. Without it, importing a tool module
during collection created its module-level `logging.FileHandler` against the
real directory, so every run appended test chatter (test paths,
`example.test` URLs) to find_new_datasets.log and friends — the files
`make status` reads.
"""

import logging
import os

import pytest

from core.log_config import PROJECT_DIR


def _real_log_dir():
    return os.path.join(PROJECT_DIR, "brain_logs")


def test_log_dir_defaults_inside_the_project():
    """Logs belong to the project, not to $HOME.

    Checked in a fresh interpreter: this session's LOG_DIR is the sandbox the
    conftest installed, so the default is only observable unpatched.
    """
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k != "BRAIN_LOG_DIR"}
    result = subprocess.run(
        [sys.executable, "-c", "import core.log_config as c; print(c.LOG_DIR)"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _real_log_dir()


def test_tests_are_sandboxed_away_from_the_real_log_dir():
    import core.log_config as log_config

    real = _real_log_dir()
    assert os.path.abspath(log_config.LOG_DIR) != os.path.abspath(real)
    assert not os.path.abspath(log_config.LOG_DIR).startswith(os.path.abspath(real) + os.sep)


@pytest.mark.parametrize(
    ("module", "logger_name"),
    [
        ("tools.find_new_datasets._log", "dl"),
        ("tools.refresh_pyramid_targets._log", "pyramid_targets"),
        ("tools.apply_discovery_and_redownload._log", "apply_disc"),
        ("tools.probe_simulation_combos._log", "probe_sim"),
    ],
)
def test_tool_file_handlers_are_sandboxed(module, logger_name):
    __import__(module)
    real_prefix = os.path.abspath(_real_log_dir()) + os.sep
    handlers = [h for h in logging.getLogger(logger_name).handlers if isinstance(h, logging.FileHandler)]
    assert handlers, f"{module} did not install its file handler"
    for handler in handlers:
        # Idempotent imports (another test may have imported first) still must
        # not point at the real directory.
        assert not os.path.abspath(handler.baseFilename).startswith(real_prefix), handler.baseFilename
