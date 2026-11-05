"""cleanup_db --backup refuses while another process holds the database."""

import subprocess
import sys

from tests import test_cleanup_db_backup_helpers as helpers
from tools import cleanup_db

# Bound here rather than imported by name: a direct import of `live_db` would
# be shadowed by the test parameters of the same name (ruff F811).
live_db = helpers.live_db


def test_backup_refuses_while_another_process_holds_the_database(live_db, tmp_path, capsys):
    """One process per file: the holder has to stop before anyone backs up."""
    path, writer = live_db
    writer.close()  # this process must let go before another can take the file
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            # The reference matters: without it the connection is garbage
            # collected and the lock is released before the assert runs.
            "import duckdb, sys, time; c = duckdb.connect(sys.argv[1]); print('held', flush=True); time.sleep(60)",
            str(path),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        assert cleanup_db.active_writer() is True
        dest = tmp_path / "refused.duckdb"
        assert cleanup_db.backup_database(str(dest)) is False
        assert not dest.exists()
        assert "another process holds the database" in capsys.readouterr().out
    finally:
        holder.kill()
        holder.wait()
