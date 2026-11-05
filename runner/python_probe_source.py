"""Static preflight for explicit, stateless MATRIX-field Python experiments.

Does not execute source or certify SDK behavior. This bounded pilot grammar
requires direct data.field access so field provenance can be checked without
evaluating arbitrary Python. It is not a security sandbox.
"""

import ast


def python_source_identity(source):
    """Ignore formatting/comments, preserving Python syntax and literal values.

    This is syntax identity, not general semantic equivalence. Unlike stripping
    whitespace it preserves string contents and block nesting.
    """
    return ast.dump(ast.parse(source), annotate_fields=True, include_attributes=False)


def validate_python_source(source, matrix_fields):
    """Return declared fields after checking syntax and explicit field access."""
    if not isinstance(source, str) or not source.strip() or len(source) > 60000:
        raise ValueError("Python source must contain 1 to 60000 characters")
    try:
        tree = ast.parse(source)
        compile(tree, "<python-probe>", "exec")
    except (SyntaxError, ValueError) as error:
        raise ValueError(f"invalid Python source: {error}") from error
    decorated = []
    imported_alpha = False
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            if any(item.name != "numpy" or item.asname != "np" for item in statement.names):
                raise ValueError("pilot imports require numpy as np")
        elif isinstance(statement, ast.ImportFrom):
            if statement.module != "brain.alphas" or statement.level or len(statement.names) != 1:
                raise ValueError("pilot only imports alpha from brain.alphas")
            item = statement.names[0]
            if item.name != "alpha" or item.asname:
                raise ValueError("alpha import must retain its name")
            imported_alpha = True
        elif isinstance(statement, ast.FunctionDef):
            if statement.args.defaults or any(value is not None for value in statement.args.kw_defaults):
                raise ValueError("pilot functions cannot have evaluated defaults")
            if statement.decorator_list:
                decorated.append(statement)
        elif not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            raise ValueError("pilot module must contain imports, functions and docstrings only")
    if not imported_alpha or len(decorated) != 1:
        raise ValueError("exactly one imported @alpha entrypoint is required")
    entry = decorated[0]
    if len(entry.decorator_list) != 1:
        raise ValueError("entrypoint must have only the alpha decorator")
    decorator = entry.decorator_list[0]
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name) or decorator.func.id != "alpha":
        raise ValueError("entrypoint requires literal @alpha(data=[...], store=[])")
    if decorator.args or len(decorator.keywords) != 2 or {k.arg for k in decorator.keywords} != {"data", "store"}:
        raise ValueError("alpha requires exactly data and store keywords")
    try:
        values = {k.arg: ast.literal_eval(k.value) for k in decorator.keywords}
    except (ValueError, TypeError) as error:
        raise ValueError("alpha declarations must be literals") from error
    fields = values["data"]
    if (
        not isinstance(fields, list)
        or not fields
        or any(not isinstance(f, str) for f in fields)
        or len(set(fields)) != len(fields)
        or not set(fields) <= set(matrix_fields)
    ):
        raise ValueError("Python data must be unique scoped MATRIX value fields")
    if values["store"] != []:
        raise ValueError("pilot Python probes must be stateless")
    args = entry.args
    if (
        args.posonlyargs
        or [a.arg for a in args.args] != ["data", "store"]
        or args.vararg
        or args.kwarg
        or args.kwonlyargs
    ):
        raise ValueError("entrypoint parameters must be data, store")
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and parents.get(node) is not tree:
            raise ValueError("nested imports are not supported")
        if isinstance(node, ast.Name) and node.id == "data":
            parent = parents.get(node)
            if not isinstance(parent, ast.Attribute) or parent.value is not node or not isinstance(node.ctx, ast.Load):
                raise ValueError("data access must be explicit data.field without aliasing")
            if not isinstance(parent.ctx, ast.Load):
                raise ValueError("data fields are read-only")
            used.add(parent.attr)
    if not used <= set(fields) | {"universe"} or not set(fields) <= used:
        raise ValueError("declared fields must be used and all data accesses declared")
    return tuple(fields)
