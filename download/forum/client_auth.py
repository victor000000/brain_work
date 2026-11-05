"""The auth flow: BRAIN login, then the SSO handoff to the support domain.

Auth flow:
  1. POST https://api.worldquantbrain.com/authentication with basic auth
  2. GET  /authentication/support?return_to=<community URL> and follow the
     redirect chain by hand — this lands the support-domain cookies on the
     session. The final HTML hop returns 403 by design; the cookies are
     already set by then, which is why the API works and the web page doesn't.
  3. GET  https://support.worldquantbrain.com/api/v2/... for content.

Split out of `download/forum/client.py`, which mixes `_AuthMixin` into
`ForumClient`.
"""

from __future__ import annotations

import json
import os
import time

import requests

from download.forum.client_config import BRAIN_API, COMMUNITY_URL, CRED_PATHS


class _AuthMixin:
    def __init__(self, cred_path: str | None = None):
        self.cred_path = cred_path or next((p for p in CRED_PATHS if os.path.exists(p)), None)
        if not self.cred_path:
            raise FileNotFoundError("no .brain_credentials found")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.authenticate()

    def authenticate(self, attempts: int = 3) -> None:
        """Rebuild the session, retrying the whole flow on transport errors.

        Every hop of the handoff is the same transient TLS class: measured
        2026-10-15, two crawl runs died uncaught inside this flow (SSLEOFError
        at the zendesk JWT hop, then at the platform `/sign-in`) while
        `get_json` sat there retrying content calls four times. An auth
        failure is the one error the content retry loop cannot survive — it
        re-raises from inside the loop's own handler — so the resilience has
        to live here, matching the explorer's own auth client.
        """
        last = None
        for attempt in range(attempts):
            try:
                self._authenticate_once()
                return
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        raise last

    def _authenticate_once(self) -> None:
        """One attempt: BRAIN auth, then the SSO handoff."""
        with open(self.cred_path) as fh:
            auth = tuple(json.load(fh))

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

        self.session.post(f"{BRAIN_API}/authentication", auth=auth, timeout=45)

        resp = self.session.get(
            f"{BRAIN_API}/authentication/support?return_to={requests.utils.quote(COMMUNITY_URL, safe='')}",
            timeout=45,
            allow_redirects=False,
        )
        hops = 0
        while resp.status_code in (301, 302, 303, 307, 308) and hops < 10:
            location = resp.headers.get("location")
            if not location:
                break
            resp = self.session.get(location, timeout=45, allow_redirects=False)
            hops += 1
