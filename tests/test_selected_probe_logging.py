"""The probe CLI keeps JSON stdout clean while retaining poll diagnostics."""

import json
import os
import subprocess
import sys


def test_inspection_records_diagnostics_without_network_or_database(tmp_path):
    script = """
import logging
import sys
from unittest.mock import MagicMock
from tools import submit_selected_probe as tool

connection = MagicMock()
connection.execute.return_value.fetchone.return_value = ('PENDING', None, '["rank(close)"]', '{}')
def get_connection():
    logging.getLogger('brain.poll').debug('test poll diagnostic')
    logging.getLogger('brain').warning('test connection warning')
    return connection
def no_auth(*args, **kwargs):
    raise AssertionError('inspection must not authenticate')
tool.get_conn = get_connection
tool.get_session = no_auth
sys.argv = ['submit_selected_probe', '--probe-id', 'selected']
tool.main()
connection.close.assert_called_once()
"""
    env = dict(os.environ, BRAIN_LOG_DIR=str(tmp_path))
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["probe_id"] == "selected"
    assert "test connection warning" in result.stderr
    assert "test poll diagnostic" in (tmp_path / "poll.log").read_text()
    assert "test connection warning" in (tmp_path / "errors.log").read_text()
