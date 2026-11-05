"""Authenticated, retrying HTTP client for the BRAIN community forum.

Sessions expire mid-run (posts come back HTTP 401). `get_json` detects that,
rebuilds the session, and retries — without this a long harvest silently
loses a quarter of its items.

Read-only: GET only.

The auth flow lives in `download.forum.client_auth`, the content endpoints in
`download.forum.client_endpoints` and the URLs/credential paths in
`download.forum.client_config`; every name is re-exported here so
`from download.forum.client import ...` keeps working.
"""

from __future__ import annotations

import time

from download.forum.client_auth import _AuthMixin
from download.forum.client_config import (  # noqa: F401
    BRAIN_API,
    COMMUNITY_URL,
    CRED_PATHS,
    PROJECT_DIR,
    SUPPORT,
)
from download.forum.client_endpoints import _EndpointsMixin


class ForumClient(_AuthMixin, _EndpointsMixin):
    """One authenticated session against the Zendesk community API."""

    def get_json(self, path: str, params: dict | None = None, retries: int = 4):
        """GET `path` and return parsed JSON, re-authenticating on session expiry."""
        url = path if path.startswith("http") else f"{SUPPORT}{path}"
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=45)
            except Exception:
                # Transient SSL/connection resets are common against this host.
                time.sleep(2 * (attempt + 1))
                continue

            if resp.status_code in (401, 403):
                # Community session expired — rebuild and retry.
                time.sleep(1 + attempt)
                self.authenticate()
                continue
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return None
            try:
                return resp.json()
            except ValueError:
                return None
        return None
