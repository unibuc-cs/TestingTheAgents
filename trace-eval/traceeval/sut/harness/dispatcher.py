"""Tool dispatcher: tool enablement, per-agent tool availability, approval gate for guarded tools,
fault injection, retries with idempotency keys, and trace events for every call."""

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
            except TypeError as exc:
                out, status = {"error": "invalid_arguments", "message": str(exc)}, "error"
        if "error" in out:
            status = "error"
        self.tracer.event(
            "tool.call",
            tool=name,
            args=args,
            status=status,
            error=out.get("error"),
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
