#!/usr/bin/env python3
"""Harvest external memory files into workspace snapshot (Phase 0a helper)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = SKILL_ROOT / "outputs" / "workspace"
PROFILE_PATH = SKILL_ROOT / "data" / "agent_profile.json"

BRAIN_KEYWORDS = re.compile(
    r"(?i)(brain|alpha|ppac|vf|value factor|turnover|sharpe|fitness|"
    r"dataset|analyst|fundamental|submission|self.?corr|operator|"
    r"region|USA|EUR|GLB|IND|delay|neutral|simulation|worldquant|模板|提交|论坛)"
)

HOST_PATHS: dict[str, list[str]] = {
    "cursor": [".cursor/rules", "AGENTS.md", ".cursorrules"],
    "claude_code": ["CLAUDE.md", "MEMORY.md"],
    "kimi": ["AGENTS.md", "memory"],
    "codex": ["AGENTS.md", ".codex", "instructions.md"],
    "windsurf": [".windsurfrules", "AGENTS.md"],
    "copilot": [".github/copilot-instructions.md"],
    "generic": ["todo.md", "README.md"],
}

SKIP_NAMES = {".env", "user_config.json", "credentials.json"}


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / ".git").exists() or (cur / "CLAUDE.md").exists() or (cur / "AGENTS.md").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def extract_bullets(text: str, max_bullets: int = 20) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "*", "•")):
            candidate = line.lstrip("-*• ").strip()
        elif re.match(r"^\d+\.", line):
            candidate = re.sub(r"^\d+\.\s*", "", line)
        else:
            candidate = line if len(line) < 200 else line[:200]
        if BRAIN_KEYWORDS.search(candidate) and candidate not in bullets:
            bullets.append(candidate)
        if len(bullets) >= max_bullets:
            break
    return bullets


def collect_paths(project_root: Path, host: str) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    order = [host] + [h for h in HOST_PATHS if h != host]
    seen: set[Path] = set()

    for h in order:
        for rel in HOST_PATHS.get(h, []):
            p = project_root / rel
            if p.is_file() and p.name not in SKIP_NAMES:
                if p not in seen:
                    seen.add(p)
                    found.append((h, p))
            elif p.is_dir():
                for f in p.rglob("*"):
                    if not f.is_file() or f.name in SKIP_NAMES:
                        continue
                    if f.suffix.lower() in {".md", ".mdc", ".txt", ".json"} and f not in seen:
                        seen.add(f)
                        found.append((h, f))
    home_claude = Path.home() / ".claude" / "CLAUDE.md"
    if home_claude.is_file() and home_claude not in seen:
        found.append(("claude_code", home_claude))
    return found


def harvest(project_root: Path | None = None, host: str | None = None) -> dict:
    if PROFILE_PATH.exists():
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        host = host or profile.get("preferred_host", "generic")
    else:
        host = host or "generic"

    root = project_root or find_project_root(SKILL_ROOT.parent.parent.parent)
    sources = []
    merged: list[str] = []

    for h, path in collect_paths(root, host):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        bullets = extract_bullets(text)
        if not bullets:
            continue
        sources.append({"path": str(path), "host": h, "bullets": bullets})
        for b in bullets:
            if b not in merged:
                merged.append(b)

    mode = "files" if sources else "session-only"
    return {
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "project_root": str(root),
        "preferred_host": host,
        "sources": sources,
        "merged_bullets": merged[:40],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--write", action="store_true", help="Write to outputs/workspace/")
    args = parser.parse_args()

    snapshot = harvest(args.project_root, args.host)
    if args.write:
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        out = WORKSPACE / "external_memory_snapshot.json"
        out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
