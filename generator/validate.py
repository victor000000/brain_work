"""Local validation for alpha expressions.

Two layers, and the split is deliberate — they do different jobs.

1. **Syntax, arity and types** — `py-fastplus` (Rust/PyO3, 108 Expert-level
   operators). It does exactly what it documents: checks argument count, type
   and operator-specific rules **when parsing known operators**. For anything
   else it is permissive by design — `src/parser.rs` returns `Ok(())` when
   `get_operator` finds no match, and `Placeholder` is a first-class AST node
   because the language supports template syntax like `<name/>`. Verified by
   reading the 0.3.5 source, not inferred.

2. **Operator allowlist** — the layer fastplus intentionally does not provide.
   Because unknown calls pass through, `totally_made_up_operator(close)` and
   `adv20(close)` (a *field* invoked as a function) both parse. Generated text
   must not contain either, so pass `known_operators`;
   `load_operator_names` reads the platform's list from the `operators` table.

Use both: syntax errors and invented operators each cost one of the 5,000 daily
simulations and return nothing.

The allowlist half lives in `generator.validate_operators`; it is re-exported
here so `from generator.validate import ...` keeps resolving.
"""

import fastplus

from generator.validate_operators import (  # noqa: F401
    _CALL_RE,
    _NOT_OPERATORS,
    called_identifiers,
    load_operator_names,
)


def _message(err: Exception) -> str:
    """Pull the message out of fastplus's caret-diagram error format."""
    for line in str(err).split("\n"):
        stripped = line.strip()
        if stripped.startswith("="):
            return stripped.lstrip("= ").strip()
    lines = [ln.strip() for ln in str(err).split("\n") if ln.strip()]
    return lines[-1] if lines else "parse error"


def parse_error(expression: str, known_operators=None) -> str | None:
    """Return a human-readable problem with `expression`, or None if it is sound.

    `known_operators` is optional. When given, any identifier called as a
    function must appear in it — which is what catches invented operators and
    fields used as functions.
    """
    if not expression or not expression.strip():
        return "empty expression"

    # fastplus accepts a leading unary '+', the platform's parser does not:
    # `+0.2*rank(...)` fails with `Unexpected character '+'`. Mined skeletons
    # produce these, and each one costs a whole simulation slot.
    if expression.lstrip().startswith("+"):
        return "leading '+' is not accepted by the platform parser"

    if known_operators is not None:
        unknown = called_identifiers(expression) - set(known_operators)
        if unknown:
            return f"unknown operator(s): {', '.join(sorted(unknown))}"

    try:
        fastplus.parse(expression)
    except Exception as err:
        return _message(err)
    return None


def is_valid(expression: str, known_operators=None) -> bool:
    """True when the expression is syntactically sound and uses known operators."""
    return parse_error(expression, known_operators) is None


def validate_batch(expressions, known_operators=None) -> tuple[list[str], list[str]]:
    """Split expressions into (valid, invalid), preserving input order."""
    valid: list[str] = []
    invalid: list[str] = []
    for expr in expressions:
        (valid if is_valid(expr, known_operators) else invalid).append(expr)
    return valid, invalid
