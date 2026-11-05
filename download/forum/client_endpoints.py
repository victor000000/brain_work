"""Community content endpoints: topics, posts, post bodies and comments.

Split out of `download/forum/client.py`, which mixes `_EndpointsMixin` into
`ForumClient`.
"""

from __future__ import annotations


class _EndpointsMixin:
    def topics(self) -> list[dict]:
        data = self.get_json("/api/v2/community/topics")
        return (data or {}).get("topics", [])

    def posts(self, topic_id: int, per_page: int = 100) -> list[dict]:
        """Every post in a topic (metadata only — bodies need `post_body`)."""
        out, page = [], 1
        while True:
            data = self.get_json(
                f"/api/v2/community/topics/{topic_id}/posts",
                {"per_page": per_page, "page": page},
            )
            if not data:
                break
            batch = data.get("posts", [])
            if not batch:
                break
            out.extend(batch)
            if page >= (data.get("page_count") or 1):
                break
            page += 1
        return out

    def post_body(self, post_id: int) -> str | None:
        """HTML body of a single post, or None when the fetch failed.

        None is deliberately distinct from "": a failed fetch must not be
        checkpointed as an empty body, or the item can never be repaired by a
        re-run (the live corpus holds 95 such bodies).
        """
        data = self.get_json(f"/api/v2/help_center/community/posts/{post_id}")
        if data is None:
            return None
        post = data.get("post")
        if not isinstance(post, dict):
            return None
        return post.get("details") or ""

    def comments(self, post_id: int, per_page: int = 100) -> list[dict] | None:
        """Every comment on a post, or None when any page failed.

        Returning the partial list on a page failure would be cached forever —
        a page-1 failure used to look like "this post has no comments".
        """
        out, page = [], 1
        while True:
            data = self.get_json(
                f"/api/v2/community/posts/{post_id}/comments",
                {"per_page": per_page, "page": page},
            )
            if data is None:
                return None
            batch = data.get("comments", [])
            if not batch:
                break
            out.extend(batch)
            if page >= (data.get("page_count") or 1):
                break
            page += 1
        return out
