"""Load BRAIN login credentials exclusively from environment or private files."""

import json
import logging
import os

from core.log import get_file_logger

log = logging.getLogger("brain")
authlog = get_file_logger("auth")


def _valid_pair(values):
    return (
        isinstance(values, (list, tuple))
        and len(values) == 2
        and all(isinstance(value, str) and value.strip() for value in values)
    )


def load_credentials(session, project_dir):
    """Prefer a complete environment pair, explicit file, then default files.

    Partial environment overrides and invalid explicitly selected files fail
    closed instead of silently authenticating with another account. Databases
    are never opened for authentication.
    """
    session.auth = None
    names = ("BRAIN_EMAIL", "BRAIN_PASSWORD")
    if any(name in os.environ for name in names):
        values = [os.environ.get(name) for name in names]
        if not _valid_pair(values):
            authlog.error("BRAIN_EMAIL and BRAIN_PASSWORD must both contain nonempty strings")
            return False
        session.auth = tuple(values)
        authlog.info("Credentials loaded from environment")
        return True

    selected = os.environ.get("BRAIN_CREDENTIALS_FILE")
    paths = (
        [selected]
        if selected is not None
        else [
            os.path.join(project_dir, ".brain_credentials"),
            os.path.expanduser("~/.brain_credentials"),
        ]
    )
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                values = json.load(handle)
        except (OSError, ValueError, TypeError) as error:
            # Exception messages can contain snippets of invalid secret input.
            authlog.debug("Credential file unavailable (%s)", type(error).__name__)
            continue
        if not _valid_pair(values):
            authlog.error("Credential file must contain a nonempty JSON [email, password] pair")
            continue
        session.auth = tuple(values)
        authlog.info("Credentials loaded from private file")
        return True
    log.error("No usable credentials found in environment or private files")
    return False
