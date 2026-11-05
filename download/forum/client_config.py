"""Endpoints and credential locations for the BRAIN community forum client.

Split out of `download/forum/client.py`, which re-exports these names.
"""

import os

BRAIN_API = "https://api.worldquantbrain.com"
SUPPORT = "https://support.worldquantbrain.com"
COMMUNITY_URL = f"{SUPPORT}/hc/en-us/community/topics"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRED_PATHS = [
    os.path.join(PROJECT_DIR, ".brain_credentials"),
    os.path.expanduser("~/.brain_credentials"),
]
