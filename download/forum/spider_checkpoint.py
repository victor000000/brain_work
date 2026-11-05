"""The forum corpus directory and the checkpoint files that make runs resume.

Split out of `download/forum/spider.py`, which re-exports these names.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "docs" / "forum"


def load_checkpoint(path) -> dict:
    """Read a checkpoint, tolerating a missing or corrupt file."""
    try:
        with open(path) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_checkpoint(path, data: dict) -> None:
    """Write a checkpoint atomically enough to survive interruption."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)


def pending_ids(all_ids, done: dict, repair_empty: bool = False) -> list:
    """Ids in `all_ids` not yet present in `done`, order preserved.

    `repair_empty` also re-queues ids whose checkpointed value is empty. A
    failed fetch used to be checkpointed as ""/[] and was then skipped forever,
    so the run has to revisit those entries to heal the corpus.
    """
    out = []
    for i in all_ids:
        key = str(i)
        if key not in done or (repair_empty and not done[key]):
            out.append(i)
    return out
