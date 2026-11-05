"""Count FASTEXPR operations without expanding reused variable bindings.

Native B11518 rejected 66 operations against a 64-operation limit. Literal
negative signs are constants, not operations. Counts are audited against
stored native expressions; syntax parsing remains a
separate gate. This is not a Python-alpha complexity limit.
"""

import fastplus


def _constant(node):
    # The wheel exposes Constant as an AST base class, not a package export.
    return any(base.__name__ == "Constant" for base in type(node).__mro__)


def _literal_prefix(node):
    # fastplus may parse -1*x as Unary(Binary(1, x)). The sign still belongs
    # to the literal. A GroupExpr stops this traversal: -(1*x) is negation.
    while type(node).__name__ == "BinaryExpr":
        node = node.left
    return _constant(node)


def _count(node):
    if _constant(node):
        return 0
    kind = type(node).__name__
    if kind == "OperationExpr":
        return 1 + sum(_count(arg) for arg in node.pos_args)
    if kind == "BinaryExpr":
        return 1 + _count(node.left) + _count(node.right)
    if kind == "UnaryExpr":
        return int(not _literal_prefix(node.expr)) + _count(node.expr)
    if kind == "TernaryExpr":
        return 1 + _count(node.cond) + _count(node.then_branch) + _count(node.else_branch)
    if kind == "GroupExpr":
        return _count(node.expr)
    if kind in ("VariableExpr", "PlaceholderExpr"):
        return 0
    raise ValueError(f"unsupported expression node for operator counting: {kind}")


def operator_count(expression):
    """Count calls and operations; count each assignment once, not per use."""
    parsed = fastplus.parse(expression)
    return sum(_count(binding.value) for binding in parsed.assignments) + _count(parsed.signal)
