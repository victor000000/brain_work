"""Authenticated access to the BRAIN tutorial/tutorial-page endpoints.

Split out of `tools/harvest_learn_docs.py`. The rendered /learn/documentation
page is a single-page app with no content in its HTML, so the documentation is
read from these two API endpoints instead.
"""

import json
import os
import time

import requests

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.worldquantbrain.com"
CRED_PATHS = [
    os.path.join(PROJECT_DIR, ".brain_credentials"),
    os.path.expanduser("~/.brain_credentials"),
]


def _retry(fn, tries=5, delay=3.0, label=""):
    """Retry on the transient SSL/connection resets this host emits."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as err:
            last = err
            print(f"    retry {i + 1}/{tries} {label}: {type(err).__name__}")
            time.sleep(delay * (i + 1))
    raise last


def authenticate(pause: float = 0.6):
    """Return an authenticated session."""
    cred = next((p for p in CRED_PATHS if os.path.exists(p)), None)
    if not cred:
        raise SystemExit("no .brain_credentials found")
    with open(cred) as fh:
        auth = tuple(json.load(fh))
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    resp = _retry(lambda: session.post(f"{BASE}/authentication", auth=auth, timeout=45), label="auth")
    if resp.status_code not in (200, 201):
        raise SystemExit(f"authentication failed: HTTP {resp.status_code}")
    time.sleep(pause)
    return session


def fetch_tutorials(session):
    """All tutorials with their page lists."""
    resp = _retry(lambda: session.get(f"{BASE}/tutorials", timeout=45), label="tutorials")
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        for key in ("results", "items", "tutorials", "data"):
            if isinstance(data.get(key), list):
                return data[key]
    return data if isinstance(data, list) else []


def fetch_page(session, page_id):
    resp = _retry(lambda: session.get(f"{BASE}/tutorial-pages/{page_id}", timeout=45), label=page_id)
    if resp.status_code != 200:
        return None
    return resp.json()
