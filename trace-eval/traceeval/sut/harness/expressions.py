"""A small, safe expression evaluator for skill procedures (whitelisted Python expression subset)."""

import ast

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
    ast.Store,
    ast.GeneratorExp,
)

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
    """dict with attribute access so procedures can write ``result.fetch.review_approved``."""

    def __getattr__(self, item):
        try:
            value = self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc
        return DotDict(value) if isinstance(value, dict) and not isinstance(value, DotDict) else value


def _check(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed expression element: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("private attribute access is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("dunder names are not allowed")


def safe_eval(expr: str, env: dict):
    tree = ast.parse(expr, mode="eval")
    _check(tree)
    scope = {"__builtins__": {}}
    scope.update(_SAFE_BUILTINS)
    scope.update(env)
    # env goes into *globals* so that comprehension scopes can see it as well
    return eval(compile(tree, "<procedure>", "eval"), scope)


def resolve_value(value, env: dict):
    """Resolve argument values: ``$name`` -> ctx variable; ``=expr`` -> evaluated expression; else literal."""
    if isinstance(value, str):
        if value.startswith("$"):
            return env["ctx"].get(value[1:])
        if value.startswith("="):
            return safe_eval(value[1:], env)
        return value
    if isinstance(value, list):
        return [resolve_value(v, env) for v in value]
    if isinstance(value, dict):
        return {k: resolve_value(v, env) for k, v in value.items()}
    return value
