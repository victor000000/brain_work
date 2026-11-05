"""Rate-limit-aware BRAIN API session for data download."""

import json
import logging
import os
import sys
import time

import requests

from core.db import connect
from download.session_throttle import ThrottleMixin

API_BASE = "https://api.worldquantbrain.com"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")
CRED_PATHS = [os.path.join(PROJECT_DIR, ".brain_credentials"), os.path.expanduser("~/.brain_credentials")]
PAGE_SIZE = 50

log = logging.getLogger("dl")


class BrainSession(ThrottleMixin):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._last_req = 0
        self._interval = 1.05

    def authenticate(self):
        for p in CRED_PATHS:
            if os.path.exists(p):
                with open(p) as f:
                    self.session.auth = tuple(json.load(f))
                log.info("Credentials from %s", p)
                break
        else:
            if os.path.exists(DB_PATH):
                conn = connect(DB_PATH)
                email_row = conn.execute("SELECT value FROM credentials WHERE key='email'").fetchone()
                pass_row = conn.execute("SELECT value FROM credentials WHERE key='password'").fetchone()
                conn.close()
                if email_row and pass_row:
                    self.session.auth = (email_row[0], pass_row[0])
                else:
                    log.error("No credentials")
                    sys.exit(1)
            else:
                log.error("No credentials file")
                sys.exit(1)
        resp = self.session.post(f"{API_BASE}/authentication")
        if resp.status_code not in (200, 201):
            log.error("Auth failed: %d", resp.status_code)
            sys.exit(1)
        self.user_id = resp.json().get("user", {}).get("id", "?")
        log.info("Authenticated as %s", self.user_id)

    def get(self, url, params=None, retries=8):
        """GET with retries. Raises the last transport error if all attempts fail.

        Returning a response here would be a lie: after `retries` consecutive
        RequestExceptions there is no response to return, and callers
        immediately touch `.status_code`. Raising surfaces the outage instead.
        """
        last_error = None
        resp = None
        for att in range(retries):
            self._throttle()
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                last_error = e
                log.warning("Req error (att %d): %s", att + 1, e)
                time.sleep(2 ** min(att, 5))
                continue
            r = self._handle(resp, url)
            if r is not None:
                log.debug("GET %s -> %d", url, r.status_code)
                return r
        log.error("Max retries for %s", url)
        if resp is None and last_error is not None:
            raise last_error
        return resp
