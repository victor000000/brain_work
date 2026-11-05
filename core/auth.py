"""BRAIN API authentication with automatic re-auth on 401.

The timeout-carrying session and the auth POST live in `core.auth_http`, the
credential lookup in `core.auth_credentials`; both are re-exported here so
`core.auth.<name>` keeps resolving for every caller and test.
"""

import os
import sys

from core.auth_credentials import load_credentials
from core.auth_http import (  # noqa: F401
    API_BASE,
    DEFAULT_HTTP_TIMEOUT,
    TIMEOUT_ENV_VAR,
    TimeoutSession,
    _authenticate,
    _default_timeout,
    _parse_timeout,
)
from core.reauth import _install_reauth_hook

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REAUTH_COOLDOWN = 30  # min seconds between re-auth attempts


class AuthError(RuntimeError):
    """Raised by get_session(raise_on_failure=True) when auth cannot be established."""


def _load_credentials(session):
    """Load credentials onto session.auth from environment or private files.

    Returns True when credentials were found, False otherwise (the caller
    decides whether to exit or raise). PROJECT_DIR is read here, at
    call time, so tests can point this module at a tmp_path.
    """
    return load_credentials(session, PROJECT_DIR)


def get_session(raise_on_failure=False):
    """Authenticate and return a requests.Session with auto re-auth.

    On failure the default (legacy) behavior is sys.exit(1), which is
    uncatchable by `except Exception` and kills embedding callers. Pass
    raise_on_failure=True to get an AuthError instead.
    """
    session = TimeoutSession()
    session.headers.update({"Accept": "application/json"})

    if not _load_credentials(session) or not _authenticate(session):
        if raise_on_failure:
            # Name the possibilities rather than pick one. The old wording
            # ("no valid credentials or auth rejected") asserted the two
            # credential-shaped causes and omitted the one that actually
            # happened on 2026-10-08 — nine times, all transport errors during
            # an afternoon of platform latency. `auth.log` has the specific
            # reason; this line is what gets read first, and it should not send
            # anyone to check credentials that were never the problem.
            raise AuthError(
                "BRAIN authentication failed — auth.log has which (credentials not loaded, "
                "transport error after retries, or the platform rejecting them)"
            )
        sys.exit(1)

    _install_reauth_hook(session, API_BASE, REAUTH_COOLDOWN)
    return session
