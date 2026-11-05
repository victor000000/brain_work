"""Credential loading for BRAIN sessions, from a file or the credentials table.

Split out of `core/auth.py`; the caller passes the project dir and DB path so
both are read at call time (tests point core.auth at a tmp_path).
"""

import json
import logging
import os

from core.db import connect
from core.log import get_file_logger

log = logging.getLogger("brain")
authlog = get_file_logger("auth")


def load_credentials(session, project_dir, db_path):
    """Load credentials onto session.auth from file or DB.

    Returns True when credentials were found, False otherwise (the caller
    decides whether to exit or raise).
    """
    for p in [os.path.join(project_dir, ".brain_credentials"), os.path.expanduser("~/.brain_credentials")]:
        if not os.path.exists(p):
            continue
        try:
            with open(p) as f:
                creds = json.load(f)
        except (OSError, ValueError) as err:
            authlog.error("Failed to read credentials from %s: %s", p, err)
            continue
        if not (isinstance(creds, list) and len(creds) == 2 and all(isinstance(c, str) for c in creds)):
            authlog.error(
                "Malformed credentials in %s: expected a JSON list of two strings [email, password]",
                p,
            )
            continue
        session.auth = (creds[0], creds[1])
        authlog.info("Credentials loaded from %s", p)
        return True
    try:
        conn = connect(db_path)
        email_row = conn.execute("SELECT value FROM credentials WHERE key='email'").fetchone()
        pass_row = conn.execute("SELECT value FROM credentials WHERE key='password'").fetchone()
        conn.close()
        if email_row and pass_row:
            session.auth = (email_row[0], pass_row[0])
            authlog.info("Credentials loaded from DB")
            return True
    except Exception as err:
        log.error("Failed to load credentials: %s", err)
    log.error("No credentials found in files or DB")
    return False
