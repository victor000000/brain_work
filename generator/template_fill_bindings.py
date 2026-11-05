"""Recover field-reference identity from an exactly matching source example."""

from __future__ import annotations

import re
from functools import lru_cache

from generator.template_fill_tokens import KEYWORDS, SLOT
from generator.validate import parse_error

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_TOKENS = re.compile(
    r"""\{f\}|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_][A-Za-z0-9_]*"""
    r"|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[^\s]"
)


def infer_slot_bindings(skeleton: str, example: object) -> tuple[int, ...] | None:
    """Return the same key for each repeated source identifier, if unambiguous.

    Every operator, literal and window must match the complete, parseable
    example. Missing/prose/placeholder examples retain legacy independent
    draws. Quoted literals are whole tokens, including their whitespace.
    """
    if not isinstance(example, str) or SLOT not in skeleton:
        return None
    return _infer(skeleton, example)


def infer_slot_sources(skeleton: str, example: object) -> tuple[str, ...] | None:
    """Source identifiers only when the complete example matches the shape."""
    if not isinstance(example, str) or infer_slot_bindings(skeleton, example) is None:
        return None
    return tuple(
        actual
        for expected, actual in zip(_TOKENS.findall(skeleton), _TOKENS.findall(example), strict=True)
        if expected == SLOT
    )


@lru_cache(maxsize=4096)
def _infer(skeleton: str, example: str) -> tuple[int, ...] | None:
    if parse_error(example) is not None:
        return None
    shape, source = _TOKENS.findall(skeleton), _TOKENS.findall(example)
    if len(shape) != len(source):
        return None
    identifiers: dict[str, int] = {}
    bindings = []
    for expected, actual in zip(shape, source, strict=True):
        if expected == SLOT:
            if not _IDENTIFIER.fullmatch(actual) or actual in KEYWORDS:
                return None
            bindings.append(identifiers.setdefault(actual, len(identifiers)))
        elif expected != actual:
            return None
    # A slot inside a quoted literal is not an input field.
    if len(bindings) != skeleton.count(SLOT):
        return None
    return tuple(bindings)
