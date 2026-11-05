#!/usr/bin/env python3
"""Validate data/agent_profile.json against schema rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = SKILL_ROOT / "data" / "agent_profile.json"
SCHEMA_PATH = SKILL_ROOT / "data" / "agent_profile.schema.json"

ALLOWED_L1 = {"commenter", "author", "linker"}
ALLOWED_HOST = {"cursor", "claude_code", "kimi", "codex", "windsurf", "copilot", "generic"}


def validate_profile(data: dict) -> list[str]:
    errors: list[str] = []

    if data.get("version") != 2:
        errors.append("version must be 2")
    if data.get("curator") is not True:
        errors.append("curator must be true")
    if data.get("write_locale") != "zh-CN":
        errors.append("write_locale must be zh-CN")

    l2 = data.get("l2")
    if not isinstance(l2, list) or len(l2) < 1:
        errors.append("l2 must be a non-empty array")

    host = data.get("preferred_host")
    if host is not None and host not in ALLOWED_HOST:
        errors.append(f"preferred_host invalid: {host}")

    history = data.get("role_history", [])
    if not isinstance(history, list):
        errors.append("role_history must be array")
    elif len(history) > 20:
        errors.append("role_history max 20 entries")
    else:
        for i, entry in enumerate(history):
            if entry.get("l1") not in ALLOWED_L1:
                errors.append(f"role_history[{i}].l1 invalid")

    return errors


def main() -> None:
    if not PROFILE_PATH.exists():
        print(f"MISSING: {PROFILE_PATH}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    errors = validate_profile(data)
    if errors:
        print("INVALID profile:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"OK: {PROFILE_PATH}")


if __name__ == "__main__":
    main()
