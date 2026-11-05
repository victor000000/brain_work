"""Map a /simulations response to (verdict, detail)."""

import json


def classify(resp):
    """Return (verdict_label, detail_text) for a /simulations HTTP response.

    Verdict labels:
      OK                    — 200/201
      REJECT_NOT_AVAILABLE  — 400 with "not available" hint (BRAIN doesn't
                              support this universe/region combo)
      REJECT_SETTINGS       — 400 mentioning universe/region/delay
      HTTP_400              — other 400
      RATE_LIMITED          — 429
      HTTP_<N>              — anything else
    """
    s = resp.status_code
    if s in (200, 201):
        return "OK", ""
    if s == 400:
        try:
            body = resp.json()
        except Exception:
            return "HTTP_400", resp.text[:200]
        txt = json.dumps(body)
        low = txt.lower()
        if "not available" in low:
            return "REJECT_NOT_AVAILABLE", txt[:240]
        if "universe" in low or "region" in low or "delay" in low:
            return "REJECT_SETTINGS", txt[:240]
        return "HTTP_400", txt[:240]
    if s == 429:
        return "RATE_LIMITED", ""
    return f"HTTP_{s}", resp.text[:200]
