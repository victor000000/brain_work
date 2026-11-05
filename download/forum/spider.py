"""Spider the BRAIN community forum: topics -> posts -> bodies -> comments.

Checkpointed at every stage so a long run resumes instead of restarting.
Comment harvesting matters most: the forum holds ~91k comments against 8.2k
posts, so post bodies alone cover roughly a tenth of the text.

Read-only.

The pieces live in `download.forum.spider_client` (one session per worker
thread), `download.forum.spider_checkpoint` (the corpus path and its resume
state), `download.forum.spider_html`, `download.forum.spider_harvest`
(comments) and `download.forum.spider_index` (topics and post metadata); they
are re-exported here so `from download.forum.spider import ...` keeps working.
`harvest_bodies` stays in this module — it is the stage driven by patching
`spider._client`.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from download.forum.spider_checkpoint import DEFAULT_OUT, load_checkpoint, pending_ids, save_checkpoint
from download.forum.spider_client import _client
from download.forum.spider_harvest import harvest_comments  # noqa: F401
from download.forum.spider_html import html_to_text  # noqa: F401
from download.forum.spider_index import harvest_index  # noqa: F401


def harvest_bodies(
    post_ids,
    out_dir=DEFAULT_OUT,
    workers: int = 12,
    verbose: bool = True,
    repair_empty: bool = True,
) -> dict:
    """Fetch the HTML body of every post id. Returns {post_id: html}.

    `repair_empty` re-fetches checkpointed empty bodies — a failed fetch used to
    be stored as "" and skipped forever. Failures (None) are counted and never
    checkpointed, so they are retried on the next run.
    """
    path = Path(out_dir) / "forum_bodies.json"
    done = load_checkpoint(path)
    todo = pending_ids(post_ids, done, repair_empty=repair_empty)
    if verbose:
        print(f"bodies: {len(done)} cached, {len(todo)} to fetch")

    if not todo:
        return done

    lock = threading.Lock()
    failures = 0
    t0 = time.time()
    n = 0

    def fetch(pid):
        return pid, _client().post_body(pid)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, pid): pid for pid in todo}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                pid, body = fut.result()
            except Exception:
                body = None
            with lock:
                n += 1
                if body is None:
                    failures += 1
                else:
                    done[str(pid)] = body
                if n % 500 == 0:
                    save_checkpoint(path, done)
                    rate = n / max(time.time() - t0, 1)
                    eta = (len(todo) - n) / max(rate, 0.01) / 60
                    if verbose:
                        print(f"  {n}/{len(todo)}  {rate:.1f}/s  eta {eta:.1f} min  fails={failures}")

    save_checkpoint(path, done)
    if verbose:
        print(f"bodies done: {len(done)} posts, {failures} failures")
    return done
