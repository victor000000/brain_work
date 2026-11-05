#!/usr/bin/env python3
"""Initialize outputs/workspace/ from templates."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"
WORKSPACE = SKILL_ROOT / "outputs" / "workspace"
RUNS = SKILL_ROOT / "outputs" / "runs"


def _copy_if_missing(src: Path, dst: Path) -> bool:
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def init_workspace(force: bool = False) -> dict:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    created = []

    mappings = [
        ("action_ledger.example.json", "action_ledger.json"),
        ("skip_registry.example.json", "skip_registry.json"),
        ("personal_experience_memory.example.md", "personal_experience_memory.md"),
        ("external_memory_snapshot.example.json", "external_memory_snapshot.json"),
    ]
    for src_name, dst_name in mappings:
        src = TEMPLATES / src_name
        dst = WORKSPACE / dst_name
        if force and dst.exists():
            dst.unlink()
        if _copy_if_missing(src, dst):
            created.append(str(dst.relative_to(SKILL_ROOT)))

    forum_memory = WORKSPACE / "forum_memory.md"
    if force and forum_memory.exists():
        forum_memory.unlink()
    if not forum_memory.exists():
        forum_memory.write_text(
            "# Forum Memory\n\nCross-session summaries appended after each Act.\n",
            encoding="utf-8",
        )
        created.append(str(forum_memory.relative_to(SKILL_ROOT)))

    return {"workspace": str(WORKSPACE), "created": created}


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def init_run(run_id: str | None = None) -> dict:
    rid = run_id or new_run_id()
    run_dir = RUNS / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for name in ("session_plan.md", "forum_findings.md", "run_contract.md", "forum_stroll_notes.md"):
        src = TEMPLATES / name
        dst = run_dir / name
        if not dst.exists():
            text = src.read_text(encoding="utf-8").replace("{{run_id}}", rid)
            dst.write_text(text, encoding="utf-8")
            created.append(str(dst.relative_to(SKILL_ROOT)))
    return {"run_id": rid, "run_dir": str(run_dir), "created": created}


def main() -> None:
    parser = argparse.ArgumentParser(description="Init brain-forum-browse workspace")
    parser.add_argument("--force", action="store_true", help="Recreate missing-template files")
    parser.add_argument("--new-run", action="store_true", help="Also create a new run folder")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    result = init_workspace(force=args.force)
    if args.new_run:
        result["run"] = init_run(args.run_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
