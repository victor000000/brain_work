"""Which `{f}` slots must be filled from the GROUP or VECTOR pool.

`fill_skeleton` drew every slot from the MATRIX pool, which `template_fill_types`
documents as a known limitation: a slot that lands where the operator needs
another type produces an expression the platform rejects, and the candidate is
discarded. Measured on the live pool 2026-10-11: of 569 usable skeletons, **110
call a group- or vector-taking operator**, and 7% of their renders were
invalid — `group_neutralize({f},{f})`, `densify({f})`, `vec_avg({f})` and
friends, where the second slot can never be anything but a series field.

The shapes whose *every* slot is mistyped were unreachable rather than merely
wasteful: `group_neutralize({f},{f})` cannot render a valid expression at all
while both slots draw from one pool, so the shape was in the pool and could
never produce a candidate. This is the same failure mode as the 21-of-38
built-ins that went unselectable, one level down.

The positions come from the platform's own operator definitions (`group_rank(x,
group)`, `vec_avg(x)`), the same source `template_fill_grouparg` uses, so the
two cannot drift: a name that wants a group there is a name that wants one here.
"""

from __future__ import annotations

import re

from generator.template_fill_args import _CALL_SITE_RE, _matching_paren
from generator.template_fill_grouparg import group_argument_indexes

# A VECTOR argument, from the platform's definitions: every `vec_*` operator
# takes the vector as its first positional argument (`vec_avg(x)`).
VECTOR_PREFIX = "vec_"
VECTOR_ARG_INDEXES = 0

_NAMED_ARG_RE = re.compile(r"[a-z_][a-z0-9_]*\s*=.*", re.IGNORECASE)


def _arg_spans(args_text: str, offset: int) -> list[tuple[int, int]]:
    """`(start, end)` of each top-level argument, in the enclosing expression."""
    spans, depth, start, i = [], 0, 0, 0
    while i < len(args_text):
        ch = args_text[i]
        if ch in "\"'":
            quote, i = ch, i + 1
            while i < len(args_text) and args_text[i] != quote:
                i += 2 if args_text[i] == "\\" else 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            spans.append((offset + start, offset + i))
            start = i + 1
        i += 1
    spans.append((offset + start, offset + len(args_text)))
    return spans


def slot_roles(skeleton: str, slot: str = "{f}") -> list[tuple[int, int, str]]:
    """`(start, end, pool)` for every slot that sits in a typed position.

    `pool` is `"group"` or `"vector"`; slots not returned are ordinary series
    slots and draw from the MATRIX pool as they always have.
    """
    out: list[tuple[int, int, str]] = []
    for match in _CALL_SITE_RE.finditer(skeleton):
        name = match.group(1).lower()
        open_idx = skeleton.index("(", match.start())
        close_idx = _matching_paren(skeleton, open_idx)
        if close_idx == -1:
            continue
        spans = _arg_spans(skeleton[open_idx + 1 : close_idx], open_idx + 1)
        args = [skeleton[a:b] for a, b in spans]

        wanted: list[tuple[tuple[int, ...], str]] = []
        if name.startswith("group_") or name in ("densify",):
            wanted.append((group_argument_indexes(name, args), "group"))
        if name.startswith(VECTOR_PREFIX):
            # Out-of-range on a malformed call is not this function's problem:
            # `parse_error` rejects it later, and guarding here would hide that.
            wanted.append(((VECTOR_ARG_INDEXES,), "vector"))

        # The nth *positional* argument's own span, not the nth span: a named
        # argument before it would shift the two apart.
        positionals = [
            (a, b) for (a, b), arg in zip(spans, args, strict=True) if not _NAMED_ARG_RE.fullmatch(arg.strip())
        ]
        for indexes, pool in wanted:
            for idx in indexes:
                if idx >= len(positionals):
                    continue
                start, end = positionals[idx]
                if skeleton[start:end].strip() == slot:
                    # Argument spans include leading whitespace; the filler
                    # looks up the exact opening brace position.
                    start += len(skeleton[start:end]) - len(skeleton[start:end].lstrip())
                    out.append((start, start + len(slot), pool))
    return out
