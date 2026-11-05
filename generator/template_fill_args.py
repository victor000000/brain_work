"""Call-site argument scanning for filled expressions.

Split out of `generator/template_fill.py`, which re-exports these names.
"""

from __future__ import annotations

import re

# A call site: identifier followed by `(`. Matched case-insensitively so
# upper-case calls are attributed to their operator before `parse_error`
# rejects them through the allowlist.
_CALL_SITE_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.IGNORECASE)


def _skip_string(text: str, start: int) -> int:
    """Index just past the string literal opening at `start`."""
    quote = text[start]
    i = start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    return i


def _matching_paren(text: str, open_idx: int) -> int:
    """Index of the `)` matching the `(` at `open_idx`, or -1."""
    depth = 0
    i = open_idx
    while i < len(text):
        ch = text[i]
        if ch in "\"'":
            i = _skip_string(text, i)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_args(args: str) -> list[str]:
    """Split a call's argument text on top-level commas, respecting quotes."""
    out, depth, start, i = [], 0, 0, 0
    while i < len(args):
        ch = args[i]
        if ch in "\"'":
            i = _skip_string(args, i)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(args[start:i])
            start = i + 1
        i += 1
    out.append(args[start:])
    return [a.strip() for a in out]


def _call_arguments(expr: str):
    """(operator name, [argument text, ...]) for every call in `expr`."""
    for m in _CALL_SITE_RE.finditer(expr):
        close = _matching_paren(expr, m.end() - 1)
        if close == -1:
            continue
        yield m.group(1), _split_args(expr[m.end() : close])


def _positional_index(args: list[str], index: int):
    """`index`-th positional argument (named `key=value` arguments skipped)."""
    positional = [a for a in args if not re.fullmatch(r"[a-z_][a-z0-9_]*\s*=.*", a, re.IGNORECASE)]
    return positional[index] if index < len(positional) else None
