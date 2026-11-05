"""Filename slugs and atomic JSON writes for the learn-documentation harvest.

Split out of `tools/harvest_learn_docs.py`, which re-exports both names so
existing imports (and tests) keep resolving.
"""

import json
import os
import re
import tempfile


def safe_name(page_id: str) -> str:
    """Turn a page id into a filename-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", page_id).strip("-")
    return slug or "page"


def write_json(path, data):
    """Write JSON atomically: temp file in the same dir, then os.replace.

    A plain open+json.dump can leave a truncated file when the process is
    interrupted; the next run then treats it as a corrupt cache and raises.
    """
    path = str(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
