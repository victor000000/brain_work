"""The forum-template mining pipeline, from corpus files to the output report.

Split out of `tools/mine_forum_templates.py`, which re-exports `main` and still
owns the argparse CLI.
"""

import json
import os

from tools.mine_forum_classify import load_reference
from tools.mine_forum_output import FORUM, report, write_rows
from tools.mine_forum_scan import build_rows, scan_documents


def main(db_path=None):
    with open(os.path.join(FORUM, "forum_bodies.json")) as fh:
        bodies = json.load(fh)
    with open(os.path.join(FORUM, "forum_comments.json")) as fh:
        comments = json.load(fh)
    with open(os.path.join(FORUM, "forum_posts.json")) as fh:
        # Bodies/comments key on the *string* post id, so the lookup below
        # (`posts.get(first)`) needs the same key shape or every row loses its
        # topic and permalink.
        posts = {str(p["id"]): p for p in json.load(fh)}
    reference = load_reference(db_path)

    skel_posts, skel_example, skel_meta, kind_count, mention, n_docs = scan_documents(bodies, comments, reference)
    rows = build_rows(skel_posts, skel_example, skel_meta, posts)
    write_rows(rows)
    report(rows, n_docs, kind_count, mention)
