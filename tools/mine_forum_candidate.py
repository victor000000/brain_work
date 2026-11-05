"""Recognize complete Fast Expression candidates without executing forum text."""

import re

from generator.validate import parse_error
from tools.mine_forum_patterns import ANY_OP_RE, PY_MARKERS, STRONG_RE

QUOTED = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
_SLOT = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_XML_SLOT = re.compile(r"<[A-Za-z_][A-Za-z0-9_:]*\s*/>")
_LABEL = re.compile(r"^(alpha|expression|expr|表达式|信号|signal)\s*[:：]\s*", re.I)  # noqa: RUF001
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)\s*(.+)$")


def strip_comments(line):
    """Retain the existing inline #/slash-comment convention."""
    spans = [(m.start(), m.end()) for m in QUOTED.finditer(line)]
    for marker in re.finditer(r"#|//", line):
        if not any(start <= marker.start() < end for start, end in spans):
            line = line[: marker.start()]
            break
    return line.strip()


def _probe(expression):
    return _SLOT.sub("forum_slot", expression)


def normalize_expression_line(line):
    """Extract a standalone assignment's RHS; retain complete programs.

    The assigned name is a label, not an input field. Only extract when the
    RHS itself parses and the original is not already a complete program.
    """
    line = strip_comments(_LABEL.sub("", line.strip())).rstrip(";").strip()
    assignment = _ASSIGN.match(line)
    if assignment and parse_error(_probe(line)) is not None:
        rhs = assignment.group(1).strip()
        if parse_error(_probe(rhs)) is None:
            return rhs
    return line


def is_named_argument(text, start, end):
    """A key inside call parentheses, rather than an input or comparison."""
    if re.match(r"\s*=(?!=)", text[end:]) is None:
        return False
    prefix = QUOTED.sub("", text[:start])
    return prefix.count("(") > prefix.count(")")


def value_tokens(text, token_pattern):
    """Value positions, excluding quoted literals and named-argument keys."""
    spans = [(m.start(), m.end()) for m in QUOTED.finditer(text)]
    for token in token_pattern.finditer(text):
        if any(start <= token.start() < end for start, end in spans):
            continue
        if not is_named_argument(text, token.start(), token.end()):
            yield token.group(0).lower()


def looks_like_alpha(line):
    line = normalize_expression_line(line)
    if _XML_SLOT.search(line) or PY_MARKERS.search(line):
        return False
    if not STRONG_RE.search(line) and not ANY_OP_RE.search(line):
        return False
    return parse_error(_probe(line)) is None
