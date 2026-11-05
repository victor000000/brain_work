"""Log-directory fixture and log lines shared by the progress-report tests."""

import pytest

from tools import progress_from_log as p


@pytest.fixture
def logdir(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "LOG_DIR", str(tmp_path))
    return tmp_path


def _write(tmp_path, name, lines):
    (tmp_path / name).write_text("\n".join(lines) + "\n")


ALPHA_OK = (
    "2026-10-05 08:40:14,184 [INFO] log_alpha:58 alpha=j281Ndo9 sh=1.92 ts=0.64 "
    "fi=1.09 to=0.2867 rn=0.00 USA/TOPSP500/d1 n=SLOW"
)
ALPHA_WEAK = (
    "2026-10-05 08:40:15,215 [INFO] log_alpha:58 alpha=xAbRXmVl sh=0.30 ts=-1.67 "
    "fi=0.06 to=0.2188 rn=0.00 HKG/TOP800/d1 n=FAST"
)
