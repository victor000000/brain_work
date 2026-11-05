"""Request wrapper for automatic re-authentication on HTTP 401."""

import logging
import threading
import time

from core.log import get_file_logger

authlog = get_file_logger("auth")

log = logging.getLogger("brain")

# After a failed re-auth attempt (exception or non-2xx), wait this long before
# trying again — long enough to avoid hammering the auth endpoint, short
# enough that a transient failure does not lock re-auth out for the full
# cooldown.
REAUTH_FAILURE_BACKOFF = 5


def _install_reauth_hook(session, api_base, reauth_cooldown):
    """Wrap session.request to auto re-authenticate on HTTP 401."""
    original_request = session.request
    session._reauthing = False
    session._last_reauth = 0
    # The same session is shared with background threads (e.g. the checker),
    # so the check-then-set of _reauthing must be atomic.
    session._reauth_lock = threading.Lock()

    def request_with_reauth(method, url, **kwargs):
        response = original_request(method, url, **kwargs)
        if response.status_code != 401:
            return response

        with session._reauth_lock:
            if session._reauthing:
                # Another thread is already re-authenticating; don't fire a
                # second auth POST.
                return response
            now = time.time()
            if now - session._last_reauth < reauth_cooldown:
                return response

            session._reauthing = True
            session._last_reauth = now
            authlog.info("HTTP 401 on %s %s — re-authenticating", method, url)
            try:
                auth_resp = original_request("POST", f"{api_base}/authentication")
            except Exception as err:
                # Must clear _reauthing or the session silently never
                # re-authenticates again for the rest of its life.
                authlog.error("Re-auth request raised: %s", err)
                session._last_reauth = now - max(reauth_cooldown - REAUTH_FAILURE_BACKOFF, 0)
                return response
            finally:
                session._reauthing = False

        status = getattr(auth_resp, "status_code", None)
        if status in (200, 201):
            authlog.info("Re-authenticated OK, retrying request")
            return original_request(method, url, **kwargs)

        authlog.error(
            "Re-auth failed: HTTP %s %s",
            status,
            getattr(auth_resp, "text", "")[:100],
        )
        # Allow a retry after the short failure backoff rather than the full
        # cooldown — a failed attempt is often transient.
        session._last_reauth = now - max(reauth_cooldown - REAUTH_FAILURE_BACKOFF, 0)
        return response

    session.request = request_with_reauth
