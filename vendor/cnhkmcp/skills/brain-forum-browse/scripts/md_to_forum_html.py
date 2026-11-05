#!/usr/bin/env python3
"""Convert Markdown draft to forum-native HTML for create_forum_comment / create_forum_post.

Supports the subset documented in references/write-style-zh.md.
Does not render Markdown in the forum — output is HTML for MCP body/details args.

Usage:
  python scripts/md_to_forum_html.py --input draft.md
  python scripts/md_to_forum_html.py --text "**bold** and `code`"
  echo "# hi" | python scripts/md_to_forum_html.py
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


def _inline(md: str) -> str:
    s = html.escape(md)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" rel="noopener noreferrer">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return s


def md_to_forum_html(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            fence = line.strip()
            lang = fence[3:].strip()
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            code = html.escape("\n".join(block))
            if lang:
                out.append(f'<pre><code class="language-{html.escape(lang)}">{code}</code></pre>')
            else:
                out.append(f"<pre><code>{code}</code></pre>")
            continue

        if re.match(r"^#{1,3}\s+", line):
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()
            tag = "h2" if level == 1 else "h3" if level == 2 else "h4"
            out.append(f"<{tag}>{_inline(title)}</{tag}>")
            i += 1
            continue

        if line.strip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].lstrip(">").strip())
                i += 1
            inner = "".join(f"<p>{_inline(q)}</p>" for q in quote_lines if q)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        if re.match(r"^[\-\*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[\-\*]\s+", lines[i]):
                items.append(re.sub(r"^[\-\*]\s+", "", lines[i]))
                i += 1
            lis = "".join(f"<li>{_inline(it)}</li>" for it in items)
            out.append(f"<ul>{lis}</ul>")
            continue

        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i]))
                i += 1
            lis = "".join(f"<li>{_inline(it)}</li>" for it in items)
            out.append(f"<ol>{lis}</ol>")
            continue

        if not line.strip():
            i += 1
            continue

        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(
            ("#", ">", "-", "*", "```")
        ) and not re.match(r"^\d+\.\s+", lines[i]):
            if lines[i].strip().startswith("```"):
                break
            para_lines.append(lines[i])
            i += 1
        body = "<br>".join(_inline(p) for p in para_lines)
        out.append(f"<p>{body}</p>")

    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown draft → forum HTML")
    parser.add_argument("--input", "-i", type=Path, help="Markdown file")
    parser.add_argument("--text", "-t", help="Markdown string")
    parser.add_argument("--output", "-o", type=Path, help="Write HTML to file")
    args = parser.parse_args()

    if args.text is not None:
        raw = args.text
    elif args.input is not None:
        raw = args.input.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    result = md_to_forum_html(raw)
    if args.output:
        args.output.write_text(result, encoding="utf-8")
        print(args.output)
    else:
        print(result)


if __name__ == "__main__":
    main()
