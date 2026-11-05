"""Comment harvesting: the bulk of the corpus, fetched concurrently.

Split out of `download/forum/spider.py`, which re-exports `harvest_comments`.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from download.forum.spider_checkpoint import DEFAULT_OUT, load_checkpoint, pending_ids, save_checkpoint
from download.forum.spider_client import _client


def harvest_comments(
    post_ids,
    out_dir=DEFAULT_OUT,
    workers: int = 12,
    verbose: bool = True,
    repair_empty: bool = True,
) -> dict:
    """Fetch comments for every post id. Returns {post_id: [comments]}.

    `repair_empty` re-fetches checkpointed empty lists — a failed page-1 fetch
    used to be cached as [] forever. Failures (None) are counted and never
    checkpointed, so they are retried on the next run.
    """
    path = Path(out_dir) / "forum_comments.json"
    done = load_checkpoint(path)
    todo = pending_ids(post_ids, done, repair_empty=repair_empty)
    if verbose:
        print(f"comments: {len(done)} cached, {len(todo)} to fetch, {workers} workers")

    if not todo:
        return done

    lock = threading.Lock()
    failures = 0
    t0 = time.time()
    n = 0

    def fetch(pid):
        comments = _client().comments(pid)
        return pid, comments

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, pid): pid for pid in todo}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                pid, comments = fut.result()
            except Exception:
                comments = None
            with lock:
                n += 1
                if comments is None:
                    failures += 1
                else:
                    done[str(pid)] = comments
                if n % 500 == 0:
                    save_checkpoint(path, done)
                    rate = n / max(time.time() - t0, 1)
                    eta = (len(todo) - n) / max(rate, 0.01) / 60
                    if verbose:
                        print(f"  {n}/{len(todo)}  {rate:.1f}/s  eta {eta:.1f} min  fails={failures}")

    save_checkpoint(path, done)
    total = sum(len(v) for v in done.values())
    if verbose:
        print(f"comments done: {len(done)} posts, {total:,} comments, {failures} failures")
    return done
