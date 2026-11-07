"""Check owned Markdown inline local links/heading fragments without network or DB access."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"\n]*")?\)')


def owned_documents(root):
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED or part.startswith(".venv") for part in rel.parts):
            continue
        if rel.parts[0] == "vendor" and rel.as_posix() != "vendor/README.md":
            continue
        yield path


def prose(text):
    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        lines.append("" if fenced else line)
    return "\n".join(lines)


def anchors(text):
    result, seen = set(), {}
    for line in prose(text).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
        if not match:
            continue
        title = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", match[1])
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        result.add(slug + (f"-{count}" if count else ""))
    return result


def check(root):
    root = Path(root).resolve()
    errors, count = [], 0
    for path in owned_documents(root):
        count += 1
        for line_no, line in enumerate(prose(path.read_text(encoding="utf-8")).splitlines(), 1):
            for match in LINK.finditer(line):
                raw = match[1].strip("<>")
                url = urlsplit(raw)
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                label = f"{path.relative_to(root)}:{line_no}: {raw}"
                if not target.is_relative_to(root):
                    errors.append(label + " escapes repository")
                elif not target.exists():
                    errors.append(label + " missing target")
                elif (
                    url.fragment
                    and target.suffix.lower() == ".md"
                    and unquote(url.fragment) not in anchors(target.read_text(encoding="utf-8"))
                ):
                    errors.append(label + " missing heading anchor")
    return count, errors


def main():
    count, errors = check(ROOT)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Checked {count} owned Markdown documents: local inline links and heading anchors passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
