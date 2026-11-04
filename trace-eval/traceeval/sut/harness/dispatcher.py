"""Tool dispatcher: tool enablement, per-agent tool availability, approval gate for guarded tools,
argument binding, fault injection, retries with idempotency keys, and trace events for every call.

Every call is traced with one status: ``ok``; ``error`` when the call was refused (a ``ToolError`` from
the tool or a gate, or arguments that do not fit the tool's signature); ``crash`` when the tool or
service code raised any other exception - a defect in the SUT, returned to the agent as ``tool_crash``
the way a tool server answers with HTTP 500."""

import inspect
import time

from ..services.errors import ToolError
from ..tools.registry import ToolContext
from .retry import with_retry


class Dispatcher:
    def __init__(self, tools: dict, config, state, tracer, faults):
        self.tools = tools
        self.config = config
        self.state = state
        self.tracer = tracer
        self.faults = faults

    def call(self, agent, name: str, args: dict, ctx: dict) -> dict:
        t0 = time.perf_counter()
        spec = self.tools.get(name)
        attempts, key, status = 0, None, "ok"
        crashed = False
        if spec is None:
            out = {"error": "unknown_tool", "message": f"tool '{name}' does not exist"}
        elif name in (self.config.get("tools.disabled") or []):
            out = {"error": "tool_disabled", "message": f"tool '{name}' is disabled by configuration"}
        elif name not in agent.tools:
            out = {"error": "tool_not_available", "message": f"agent '{agent.name}' cannot use '{name}'"}
        elif self._needs_approval(spec, name) and not ctx.get("approval_token"):
            out = {
                "error": "approval_required",
                "message": f"'{name}' is a guarded operation and requires an approval token",
            }
        elif (bad_args := _argument_error(spec, args)) is not None:
            out = {"error": "invalid_arguments", "message": bad_args}
        else:

            def attempt(idem_key):
                self.faults.before(name)
                tctx = ToolContext(
                    state=self.state,
                    config=self.config,
                    user_id=ctx.get("user_id", "anonymous"),
                    approval_token=ctx.get("approval_token"),
                    idempotency_key=idem_key,
                )
                result = spec.fn(tctx, **args)
                self.faults.after(name)
                return result

            try:
                out, attempts, key = with_retry(
                    attempt,
                    retries=int(self.config.get("runtime.retries") or 0),
                    is_write=spec.is_write(),
                    idempotency_enabled=bool(self.config.get("runtime.idempotency_keys")),
                )
            except ToolError as exc:
                out, status = exc.to_dict(), "error"
            except Exception as exc:  # noqa: BLE001 - any other exception is a defect in tool or service code
                out, crashed = {"error": "tool_crash", "message": f"{type(exc).__name__}: {exc}"}, True
        if "error" in out:
            status = "error"
        if crashed:
            status = "crash"
        self.tracer.event(
            "tool.call",
            tool=name,
            args=args,
            status=status,
            error=out.get("error"),
            message=out.get("message") if status != "ok" else None,
            attempts=attempts,
            idempotency_key=key,
            tool_kind=spec.kind if spec else None,
            agent=agent.name,
            duration_ms=round((time.perf_counter() - t0) * 1000, 3),
        )
        return out

    def _needs_approval(self, spec, name: str) -> bool:
        gated = self.config.get("tools.requires_approval") or []
        return spec.kind == "guarded" and name in gated


def _argument_error(spec, args: dict) -> str | None:
    """Why ``args`` do not fit the adapter signature (the agent's mistake), or None. Checked before the
    call so that a TypeError raised *inside* a tool is reported as a crash, not as bad arguments."""
    try:
        inspect.signature(spec.fn).bind(None, **args)
    except TypeError as exc:
        return str(exc)
    return None
