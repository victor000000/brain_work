"""Prose and assignment recovery for mined skeletons.

The two shapes that dominate the corpus's unusable half, both mechanical.
Split out of `generator/template_fill.py`, which re-exports these names.
"""

from __future__ import annotations

import re

from generator.template_fill_usable import skeleton_shape_problem

# A leading `name = ` assignment (variable names can be any language: the
# corpus has `组件A = ts_rank({f},10)` as well as `alpha = ...`). The filler
# substitutes fields into every slot and a field cannot be assigned to, so the
# RHS is the expression; `==` and the comparison operators are excluded.
_ASSIGNMENT = re.compile(r"^\s*[^\s=()<>!]+(?:[^=()<>!]*?)\s*=\s*(?!=)(.+)$", re.DOTALL)

_CALL_START = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\s*\(")

# A balanced span can still end on an operator when the prose cut it off
# ("abs({f}-group_mean({f},1,market))/") — the expression is what precedes it.
_TRAILING_OPERATORS = re.compile(r"[\s*/+,-]+$")


def _balanced_candidates(text: str) -> list[str]:
    """Balanced-paren substrings starting at each call site, longest first."""
    out = []
    for m in _CALL_START.finditer(text):
        start = m.start()
        while start > 0 and text[start - 1] in "-+.":
            start -= 1
        depth = 0
        for i in range(m.end() - 1, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    out.append(_TRAILING_OPERATORS.sub("", text[start : i + 1].strip()))
                    break
    # Ties are broken by the text itself: `set` iteration order varies with
    # PYTHONHASHSEED, so a length-only key would make the skeleton a line
    # cleans to depend on the interpreter's hash seed.
    return sorted(set(out), key=lambda s: (-len(s), s))


def clean_skeleton(skeleton: str, known_operators=None) -> str:
    """The expression core of a mined line, or the input unchanged.

    Two shapes dominate the corpus's unusable half, and both are mechanical:
    prose around a formula ("sort by volume: rank({f}) on today's volume.") and
    one-line assignments ("组件A = ts_rank({f},10)"). Stripping the assignment
    and taking the longest parseable balanced call recovers ~500 skeletons from
    the ~1,040 the shape check rejects; filled and validated like any other
    skeleton, they are ordinary templates (99% of the rescued are productive).

    Anything without a parseable core is returned unchanged for `is_usable`
    to reject — cleaning must never fabricate an expression the line does not
    contain, so every candidate is judged by the same `skeleton_shape_problem`.
    """
    if skeleton_shape_problem(skeleton, known_operators) is None:
        return skeleton
    match = _ASSIGNMENT.match(skeleton)
    base = match.group(1).strip() if match else skeleton
    if match and skeleton_shape_problem(base, known_operators) is None:
        return base
    for candidate in _balanced_candidates(base):
        if skeleton_shape_problem(candidate, known_operators) is None:
            return candidate
    return skeleton
