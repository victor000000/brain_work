"""The forum index: topics and every post's metadata.

Split out of `download/forum/spider.py`, which re-exports `harvest_index`.
"""

from __future__ import annotations

import json
from pathlib import Path

from download.forum.client import ForumClient
from download.forum.spider_checkpoint import DEFAULT_OUT


def harvest_index(out_dir=DEFAULT_OUT, verbose: bool = True) -> list[dict]:
    """Fetch topics and every post's metadata. Returns the post index."""
    path = Path(out_dir) / "forum_posts.json"
    client = ForumClient()
    posts = []
    for topic in client.topics():
        batch = client.posts(topic["id"])
        for p in batch:
            p["topic_name"] = topic["name"]
        posts.extend(batch)
        if verbose:
            print(f"  {topic['name'][:44]:46} {len(batch):5} posts")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(posts, fh, ensure_ascii=False)
    if verbose:
        print(f"index: {len(posts)} posts")
    return posts
