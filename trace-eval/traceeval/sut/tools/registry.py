"""Tool registry: declarative tool specifications.

Each adapter module declares its tools with the ``@tool`` decorator, which files a ``ToolSpec`` in ``TOOLS``
when the module is imported. The dispatcher runs tools from that table, and the LLM backend turns each spec
into the JSON schema that tells the model how to call the tool. Every loaded copy of the platform has a
registry of its own."""

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Every registered tool, by name; filled as the adapter modules are imported.
TOOLS: dict[str, "ToolSpec"] = {}

# How a Python parameter type is named in the JSON schema shown to the model. A type that is not listed
# here, or a parameter without a type hint, is described as a string.
_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


@dataclass
class ToolContext:
    """Execution context handed to every tool adapter by the dispatcher.

    It carries what an adapter needs but the model does not choose: the platform data, the configuration,
    the user the agent acts for and the request's approval token. The dispatcher builds a new context for
    every try of a call. For a write tool the retry policy also adds an idempotency key (when the
    configuration enables keys), and all tries of one call carry the same key."""

    state: Any  # the platform's in-memory data (pages, assets, users, audit log) that the services read and change
    config: Any  # the runtime configuration; each lookup through it is recorded in the trace
    user_id: str  # the user the agent acts for, from the request ("anonymous" when it names none)
    approval_token: str | None = None  # token of the user who approves a guarded call; None if the request has none
    idempotency_key: str | None = None  # set on write calls, so a service can recognise a retry and not repeat it


@dataclass
class ToolSpec:
    """One registered tool: its name and kind, what the model is told about it, and the adapter to call.

    The kind decides how a call is treated. ``read`` tools look data up. ``write`` and ``guarded`` tools
    change it, and their calls get an idempotency key in case they are retried; a guarded tool also needs an
    approval token when the configuration lists it under ``tools.requires_approval``. The one ``control``
    tool, ``route_to_agent``, is handled by the runtime and never reaches the dispatcher."""

    name: str
    kind: str  # "read" | "write" | "guarded" | "control"
    description: str  # what the tool does, as the model reads it in the tool schema
    fn: Callable  # the adapter; the dispatcher calls it as fn(ToolContext, **arguments)
    params: dict[str, str] = field(default_factory=dict)  # parameter name -> description shown to the model

    def schema(self) -> dict:
        """OpenAI function-calling schema derived from the adapter signature.

        The LLM backend sends this schema to the model for every tool the agent may use. Parameter types
        come from the adapter's type hints, their descriptions from ``params``, and a parameter without a
        default value is marked as required."""
        sig = inspect.signature(self.fn)
        props, required = {}, []
        for pname, p in sig.parameters.items():
            # The context is supplied by the dispatcher, so the model never sees it.
            if pname == "ctx":
                continue
            ann = p.annotation
            origin = getattr(ann, "__origin__", None)
            # A parameter annotated ``list`` or ``list[...]`` is described as a list of strings, whatever the
            # item type.
            if origin is list or ann is list:
                jt = {"type": "array", "items": {"type": "string"}}
            else:
                # A type with arguments, such as ``str | None``, is described by its first argument that is not
                # None. An optional list therefore gets a bare "array" here, without the string items above.
                base = ann
                if getattr(ann, "__args__", None):  # Optional[str] -> str
                    base = [a for a in ann.__args__ if a is not type(None)][0]
                jt = {"type": _JSON_TYPES.get(base, "string")}
            # The decorator's hint for this parameter, or just its name when the decorator gives none.
            jt["description"] = self.params.get(pname, pname)
            props[pname] = jt
            if p.default is inspect.Parameter.empty:
                required.append(pname)
        # One entry of the "tools" list in an OpenAI-style chat-completions request.
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }

    def is_write(self) -> bool:
        """True for the tools that change platform data, ``write`` and ``guarded``. The retry policy gives
        every call of such a tool an idempotency key (when the configuration enables keys), so that a service
        that honours the key can recognise a retry instead of applying the change twice."""
        return self.kind in ("write", "guarded")


def tool(name: str, kind: str, description: str, params: dict[str, str] | None = None):
    """Decorator that registers the function below it as a tool.

    ``name`` is what agents call the tool by and ``kind`` is one of read, write, guarded or control;
    ``description`` and ``params`` (one hint per parameter) are what the model is told about the tool. The
    function itself is returned unchanged. Registering a second tool under the same name replaces the first."""

    def deco(fn):
        TOOLS[name] = ToolSpec(name=name, kind=kind, description=description, fn=fn, params=params or {})
        return fn

    return deco
