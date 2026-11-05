"""The loaded, filtered and cached mined-template pool.

Split out of `generator/template_source.py`, which re-exports these names so
`from generator import template_source as ts` keeps seeing them.
"""

from __future__ import annotations

import json
import os
import threading

from core.log import get_file_logger
from generator.template_fill import clean_skeleton, is_usable
from generator.template_fill_bindings import infer_slot_bindings
from generator.template_fill_prices import price_contract
from generator.template_source_corpus import TEMPLATE_PATHS, _corpus_label, _normalise

glog = get_file_logger("generator")

_lock = threading.Lock()
_pool: list[dict] = []
_pool_signature: tuple | None = None


def load_pool(fields, known_operators, path=None) -> list[dict]:
    """Usable skeletons from every mined corpus. Cached until the pools change.

    `path` is a single file (tests), a sequence of files, or None for
    `TEMPLATE_PATHS`. Rows deduplicate by skeleton and source-reference identity
    across files: different repeated-field graphs remain distinct.

    Keyed on the pool's *contents* — a hash of the sorted field names plus the
    operator count, the paths, and each file's stamp. Sizing alone was wrong:
    two regions whose pools hold the same number of fields shared one filtered
    pool, so the second region was handed skeletons filtered against the first
    one's fields. The file stamp (mtime + size) means a re-mine is picked up at
    the next load without restarting the explorer.
    """
    global _pool, _pool_signature
    if path is None:
        paths: tuple[str, ...] = TEMPLATE_PATHS
    elif isinstance(path, (str, os.PathLike)):
        # A single path. Without the PathLike case a `pathlib.Path` falls into
        # `tuple(path)` and is read as a sequence of its own components.
        paths = (os.fspath(path),)
    else:
        paths = tuple(os.fspath(p) for p in path)
    stamps = []
    for p in paths:
        try:
            st = os.stat(p)
            stamps.append((p, st.st_mtime_ns, st.st_size))
        except OSError:
            stamps.append((p, None, None))
    # `known_operators` is keyed on its *contents*, not its size, for the same
    # reason `fields` is: a refreshed operator table can swap one name for
    # another and leave the count unchanged, and a pool filtered against the
    # old set would then be reused — admitting skeletons calling an operator
    # the platform no longer has.
    signature = (
        tuple(stamps),
        hash(tuple(sorted(fields))),
        hash(tuple(sorted(known_operators or ()))),
    )
    with _lock:
        if _pool_signature == signature:
            return _pool

    rows: list[dict] = []
    seen: set[tuple] = set()
    for p in paths:
        if not os.path.exists(p):
            glog.warning("no mined templates at %s", p)
            continue
        corpus = _corpus_label(p)
        with open(p) as fh:
            for r in _normalise(json.load(fh)):
                # Reduce the line to its expression core before dedup: prose
                # and assignment forms collapse to the same skeleton, and the
                # duplicates they share should count once.
                skeleton = clean_skeleton(r["skeleton"], known_operators)
                bindings = infer_slot_bindings(skeleton, r.get("example"))
                # An all-distinct example has the same behavior as legacy
                # independent slots. Different repeated-reference graphs do not.
                identity = bindings if bindings and len(set(bindings)) < len(bindings) else None
                key = skeleton, identity, price_contract(skeleton, r.get("example"))
                if key not in seen:
                    seen.add(key)
                    rows.append({**r, "skeleton": skeleton, "corpus": corpus, "slot_bindings": bindings})
    pool = [r for r in rows if is_usable(r["skeleton"], fields, known_operators)]
    glog.info("template pool: %d usable of %d mined (%d file(s))", len(pool), len(rows), len(paths))

    with _lock:
        _pool, _pool_signature = pool, signature
    return pool


def reset_cache() -> None:
    """Drop the cached pool (tests, or after re-mining)."""
    global _pool, _pool_signature
    with _lock:
        _pool, _pool_signature = [], None
