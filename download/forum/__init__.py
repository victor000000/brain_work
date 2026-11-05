"""Read-only spider for the WorldQuant BRAIN community forum.

Reaches the Zendesk-hosted forum over plain HTTP — no headless browser. The
BRAIN API authenticates the account, `/authentication/support` performs the
SSO handoff and sets the support-domain cookies, and the Zendesk Community API
then serves topics, posts and comments directly.

Read-only: this package issues GETs only.
"""

from download.forum.client import ForumClient

__all__ = ["ForumClient"]
