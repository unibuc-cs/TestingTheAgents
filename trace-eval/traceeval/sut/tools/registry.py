"""Tool registry: declarative tool specifications shared by the simulated and the LLM backends."""

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

TOOLS: dict[str, "ToolSpec"] = {}

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


@dataclass
class ToolContext:
    """Execution context handed to every tool adapter by the dispatcher."""

    state: Any
    config: Any
    user_id: str
    approval_token: str | None = None
    idempotency_key: str | None = None


@dataclass
class ToolSpec:
    name: str
    kind: str  # "read" | "write" | "guarded" | "control"
    description: str
    fn: Callable
    params: dict[str, str] = field(default_factory=dict)
    module: str = ""

    def schema(self) -> dict:
        """OpenAI function-calling schema derived from the adapter signature."""
        sig = inspect.signature(self.fn)
        props, required = {}, []
        for pname, p in sig.parameters.items():
            if pname == "ctx":
                continue
            ann = p.annotation
            origin = getattr(ann, "__origin__", None)
            if origin is list or ann is list:
                jt = {"type": "array", "items": {"type": "string"}}
            else:
                base = ann
                if getattr(ann, "__args__", None):  # Optional[str] -> str
                    base = [a for a in ann.__args__ if a is not type(None)][0]
                jt = {"type": _JSON_TYPES.get(base, "string")}
            jt["description"] = self.params.get(pname, pname)
            props[pname] = jt
            if p.default is inspect.Parameter.empty:
                required.append(pname)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }

    def is_write(self) -> bool:
        return self.kind in ("write", "guarded")


def tool(name: str, kind: str, description: str, params: dict[str, str] | None = None):
    def deco(fn):
        spec = ToolSpec(
            name=name,
            kind=kind,
            description=description,
            fn=fn,
            params=params or {},
            module=fn.__module__.rsplit(".", 1)[-1],
        )
        TOOLS[name] = spec
        return fn

    return deco


def get_tool(name: str) -> ToolSpec | None:
    return TOOLS.get(name)
