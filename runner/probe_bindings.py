"""Expand sequential FASTEXPR bindings for validation, never for submission."""

import re

from generator.template_fill_tokens import GROUP_NAMES, KEYWORDS

_TOKEN = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_][A-Za-z0-9_]*|;""")
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)(.+)$", re.S)
MAX_EXPANDED_LENGTH = 200_000


def validation_expressions(expression, reserved):
    """Return expanded RHSs and output; reject shadowing and unused bindings.

    Validation of every returned expression catches forward references,
    out-of-scope fields and type misuse even in intermediate calculations.
    Quoted literals are preserved. The submitted text is left untouched.
    """
    cuts = [m.start() for m in _TOKEN.finditer(expression) if m.group() == ";"]
    if not cuts:
        return [expression]
    parts, start = [], 0
    for end in cuts:
        parts.append(expression[start:end].strip())
        start = end + 1
    parts.append(expression[start:].strip())
    if not all(parts):
        raise ValueError("probe bindings require assignments followed by one output expression")
    bindings, references, expanded = {}, {}, []
    forbidden = set(reserved) | KEYWORDS | GROUP_NAMES

    def expand(text):
        used = set()

        def replace(match):
            name = match.group()
            if name not in bindings:
                return name
            used.add(name)
            value = bindings[name]
            return value if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) else "(" + value + ")"

        result = _TOKEN.sub(replace, text)
        if len(result) > MAX_EXPANDED_LENGTH:
            raise ValueError("probe binding expansion exceeds validation limit")
        return result, used

    for part in parts[:-1]:
        match = _ASSIGN.fullmatch(part)
        if not match:
            raise ValueError("only sequential assignments may precede probe output")
        name, rhs = match.groups()
        if name in forbidden or name in bindings:
            raise ValueError("probe binding shadows a field, operator, keyword or prior binding")
        value, used = expand(rhs.strip())
        bindings[name], references[name] = value, used
        expanded.append(value)
    if _ASSIGN.fullmatch(parts[-1]):
        raise ValueError("probe requires a final output expression")
    output, used = expand(parts[-1])
    pending = list(used)
    while pending:
        for dependency in references[pending.pop()]:
            if dependency not in used:
                used.add(dependency)
                pending.append(dependency)
    if used != set(bindings):
        raise ValueError("unused probe binding")
    return [*expanded, output]
