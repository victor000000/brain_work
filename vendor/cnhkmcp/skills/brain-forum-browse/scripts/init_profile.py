#!/usr/bin/env python3
"""Interactive or CLI bootstrap for data/agent_profile.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = SKILL_ROOT / "data" / "agent_profile.json"
EXAMPLE_PATH = SKILL_ROOT / "data" / "agent_profile.example.json"

L2_OPTIONS = [
    "PPAC",
    "VF",
    "beginner",
    "correlation",
    "SuperAlpha",
    "templates",
    "region",
    "dataset",
]
HOST_OPTIONS = ["cursor", "claude_code", "kimi", "codex", "windsurf", "copilot", "generic"]


def build_profile(
    l2: list[str],
    region: str | None = None,
    dataset: str | None = None,
    preferred_host: str = "generic",
    index_opt_in: bool = False,
) -> dict:
    return {
        "version": 2,
        "curator": True,
        "preferred_host": preferred_host,
        "l2": l2,
        "l2_params": {"region": region, "dataset": dataset},
        "write_locale": "zh-CN",
        "index_protocol_opt_in": index_opt_in,
        "upvoted_comment_ids": [],
        "role_history": [],
    }


def interactive() -> dict:
    print("brain-forum-browse profile bootstrap (L2 only, no L1)\n")
    print("L2 options:", ", ".join(L2_OPTIONS))
    raw = input("Pick 1-3 L2 tags (comma-separated): ").strip()
    l2 = [x.strip() for x in raw.split(",") if x.strip()]
    if not l2:
        raise SystemExit("At least one L2 tag required.")
    region = input("Optional region (USA/EUR/GLB/IND or empty): ").strip() or None
    dataset = input("Optional dataset id or empty: ").strip() or None
    host = input(f"Preferred host [{', '.join(HOST_OPTIONS)}] (default generic): ").strip() or "generic"
    if host not in HOST_OPTIONS:
        host = "generic"
    opt = input("Index post protocol opt-in? [y/N]: ").strip().lower()
    return build_profile(l2, region, dataset, host, opt in ("y", "yes"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--l2", nargs="+", help="L2 specialty tags")
    parser.add_argument("--region", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--host", default="generic", choices=HOST_OPTIONS)
    parser.add_argument("--index-opt-in", action="store_true")
    parser.add_argument("--from-example", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if PROFILE_PATH.exists() and not args.force:
        raise SystemExit(f"Profile exists: {PROFILE_PATH} (use --force)")

    if args.from_example:
        profile = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    elif args.l2:
        profile = build_profile(args.l2, args.region, args.dataset, args.host, args.index_opt_in)
    else:
        profile = interactive()

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {PROFILE_PATH}")


if __name__ == "__main__":
    main()
