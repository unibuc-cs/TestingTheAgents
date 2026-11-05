"""A small, safe expression evaluator for skill procedures (whitelisted Python expression subset).

Procedures use expressions in ``when`` and ``require`` conditions, in ``=expr`` values (of step arguments
and ``set`` steps) and in the ``{expr}`` placeholders of messages. The names an expression can use come
from the caller: the simulated backend passes ``ctx``, ``result``, ``last``, ``intent``, ``request`` and
``config``.
"""

import ast

# The only syntax an expression may contain: literals, names, attribute and item access, slices,
# comparisons, boolean logic, + - * / %, conditional expressions, calls with positional arguments, list
# comprehensions, generator expressions and f-strings. Anything else, such as a lambda, an assignment
# expression, a keyword argument, a set literal, a set or dict comprehension, or the // and ** operators,
# is rejected before evaluation.
_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.List,
    ast.Dict,
    ast.Tuple,
    ast.IfExp,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.USub,
    ast.Load,
    ast.ListComp,
    ast.comprehension,
    ast.Slice,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.Store,  # the loop variable of a comprehension is an assignment target
    ast.GeneratorExp,
)

# The only built-in functions an expression can call; Python's real builtins are hidden from it.
_SAFE_BUILTINS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "any": any,
    "all": all,
    "sorted": sorted,
    "min": min,
    "max": max,
    "list": list,
    "set": set,
    "round": round,
    "abs": abs,
}


class DotDict(dict):
    """dict with attribute access so procedures can write ``result.fetch.review_approved``.

    Nested dicts are wrapped as they are reached, so the dotted form works at any depth; dicts inside a
    list are not wrapped and need brackets (``b['link']``). A key named like a dict method, such as
    ``items`` or ``get``, still gives the method, so such keys must be read with brackets too.
    """

    def __getattr__(self, item):
        """Look a missing attribute up as a key. Python calls this only when normal attribute lookup
        fails, which is why dict methods win over keys of the same name. A missing key raises
        AttributeError, just as a missing attribute would."""
        try:
            value = self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc
        return DotDict(value) if isinstance(value, dict) and not isinstance(value, DotDict) else value


def _check(tree: ast.AST):
    """Raise ValueError if the parsed expression uses anything outside the whitelist: a node type that is
    not in ``_ALLOWED_NODES``, an attribute whose name starts with an underscore, or a name that starts
    with a double underscore. These rules keep expressions away from Python internals such as
    ``obj.__class__`` or ``__import__``."""
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed expression element: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("private attribute access is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("dunder names are not allowed")


def safe_eval(expr: str, env: dict):
    """Evaluate one whitelisted expression with the names in ``env`` and return its value.

    Raises ValueError for syntax outside the whitelist and SyntaxError for text that is not an expression
    at all. Errors raised while evaluating, such as a missing key, reach the caller unchanged.
    """
    # Everything is checked before anything runs.
    tree = ast.parse(expr, mode="eval")
    _check(tree)
    # The expression sees no real builtins, only the safe ones and the caller's names (which win over a
    # safe builtin of the same name).
    scope = {"__builtins__": {}}
    scope.update(_SAFE_BUILTINS)
    scope.update(env)
    # env goes into *globals* so that comprehension scopes can see it as well
    return eval(compile(tree, "<procedure>", "eval"), scope)


def resolve_value(value, env: dict):
    """Resolve argument values: ``$name`` -> ctx variable; ``=expr`` -> evaluated expression; else literal.

    Lists and dicts are resolved element by element, at any depth. A ``$name`` that is not in the context
    resolves to None.
    """
    # Only strings carry the two markers; any other string is taken literally.
    if isinstance(value, str):
        if value.startswith("$"):
            return env["ctx"].get(value[1:])
        if value.startswith("="):
            return safe_eval(value[1:], env)
        return value
    # Containers are resolved element by element, so one argument dict can mix literals and references.
    if isinstance(value, list):
        return [resolve_value(v, env) for v in value]
    if isinstance(value, dict):
        return {k: resolve_value(v, env) for k, v in value.items()}
    return value
