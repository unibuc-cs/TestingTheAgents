"""Tool dispatcher: tool enablement, per-agent tool availability, approval gate for guarded tools,
argument binding, fault injection, retries with idempotency keys, and trace events for every call.

Every call is traced with one status: ``ok``; ``error`` when the call was refused (a ``ToolError`` from
the tool or a gate, or arguments that do not fit the tool's signature); ``crash`` when the tool or
service code raised any other exception - a defect in the SUT, returned to the agent as ``tool_crash``
the way a tool server answers with HTTP 500."""

import inspect
import json
import time

from ..services.errors import ToolError
from ..tools.registry import ToolContext
from .retry import with_retry


class Dispatcher:
    """The single door between the agents and the tools.

    Agents never call a tool function themselves: the runtime hands every tool request to ``call``,
    which decides whether the call may run at all, runs it (with fault injection and retries) and
    records what happened in the trace. Because every call passes through here, these rules hold for
    every agent and every skill alike.
    """

    def __init__(self, tools: dict, config, state, tracer, faults):
        self.tools = tools  # tool name -> ToolSpec, the registry filled by the @tool decorators in tools/
        self.config = config  # runtime settings: config/runtime.yaml plus any per-test overrides
        self.state = state  # the in-memory platform data that the tools read and change
        self.tracer = tracer  # receives one "tool.call" event per call; scorers and selectors read them
        self.faults = faults  # the test's fault profile, fired just before and just after a tool runs
        self.request_id = None  # the request being served, set by start_request; part of every write's key
        self._succeeded: dict[str, int] = {}  # call identity -> how often that call has succeeded in this request

    def start_request(self, request_id: str):
        """Begin serving request ``request_id``: the idempotency keys of its writes are derived from it."""
        self.request_id = request_id
        self._succeeded = {}

    def _call_identity(self, name: str, args: dict) -> str:
        """What a call does, within the current request: the tool and its arguments, written out in a fixed
        order so that equal arguments always give the same text."""
        return f"{self.request_id}|{name}|{json.dumps(args, sort_keys=True, default=str)}"

    def call(self, agent, name: str, args: dict, ctx: dict) -> dict:
        """Run one tool call on behalf of ``agent`` and return what the agent gets back.

        ``args`` are the arguments the agent chose and ``ctx`` is the request context (user id, approval
        token, ...). The answer is either the tool's own result or an ``{"error": ..., "message": ...}``
        dict: the agent always receives a dict, never an exception.
        """
        # What the trace event at the end reports about the call: when it started, how many tries it took (0 when
        # a gate refuses it), the write's idempotency key, and whether it ended ok, refused or crashed.
        t0 = time.perf_counter()
        spec = self.tools.get(name)
        attempts, key, status = 0, None, "ok"
        crashed = False
        # The gates are checked in order. The first one that refuses the call answers for it, and the
        # tool itself never runs. First: a tool the platform does not know at all (an LLM can invent one).
        if spec is None:
            out = {"error": "unknown_tool", "message": f"tool '{name}' does not exist"}
        # A real tool, but switched off for the whole platform by a feature flag in the configuration.
        elif name in (self.config.get("tools.disabled") or []):
            out = {"error": "tool_disabled", "message": f"tool '{name}' is disabled by configuration"}
        # A real tool, but not one that this agent's definition allows it to use.
        elif name not in agent.tools:
            out = {"error": "tool_not_available", "message": f"agent '{agent.name}' cannot use '{name}'"}
        # Guarded tools (approving a review, exporting personal data, taking a page down) need an approval
        # token in the request. Only its presence is checked here; services that care compare it with the
        # token of the user who is supposed to approve.
        elif self._needs_approval(spec, name) and not ctx.get("approval_token"):
            out = {
                "error": "approval_required",
                "message": f"'{name}' is a guarded operation and requires an approval token",
            }
        # The arguments do not fit the tool's signature: the agent got the call itself wrong.
        elif (bad_args := _argument_error(spec, args)) is not None:
            out = {"error": "invalid_arguments", "message": bad_args}
        else:
            # Every gate passed, so the tool runs.

            def attempt(idem_key):
                # One try. The fault injector may fail it before the tool runs (the call never happened)
                # or after it ran (the change was made, but the acknowledgement was lost on the way back).
                # The try is counted and its key kept here, so that the trace has both even when the last
                # try fails and with_retry raises instead of returning them.
                nonlocal attempts, key
                attempts, key = attempts + 1, idem_key
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

            # with_retry repeats tries that failed transiently. Write tools get an idempotency key, so that a
            # retry after a lost acknowledgement does not apply the same change a second time. The key is
            # derived from what the call does and how often that call has already succeeded in this request.
            # So the agent making a failed call again (after a lost acknowledgement, say) repeats the same
            # operation and gets the same key, while the same call made again after it went through is a new
            # operation with a new key.
            call_identity = self._call_identity(name, args)
            try:
                out, attempts, key = with_retry(
                    attempt,
                    retries=int(self.config.get("runtime.retries") or 0),
                    is_write=spec.is_write(),
                    idempotency_enabled=bool(self.config.get("runtime.idempotency_keys")),
                    operation=f"{call_identity}#{self._succeeded.get(call_identity, 0)}",
                )
            except ToolError as exc:
                # An expected refusal from the tool or a service (not found, permission denied, ...), or a
                # transient failure that was still failing after the last retry.
                out, status = exc.to_dict(), "error"
            except Exception as exc:  # noqa: BLE001 - any other exception is a defect in tool or service code
                # Any other exception is a bug in the tool or service code. The agent still gets an error
                # result, like the HTTP 500 a real tool server would send, and the trace records a crash.
                out, crashed = {"error": "tool_crash", "message": f"{type(exc).__name__}: {exc}"}, True
        # The status written to the trace: a refusal by a gate or by the tool is "error", and a crash wins
        # over that.
        if "error" in out:
            status = "error"
        if crashed:
            status = "crash"
        # A write that went through: making the same call again in this request is a new operation.
        if key is not None and status == "ok":
            self._succeeded[call_identity] = self._succeeded.get(call_identity, 0) + 1
        # One trace event per call, whatever happened. The scorers, the selectors and the spec checks all
        # work from these events.
        self.tracer.event(
            "tool.call",
            tool=name,
            args=args,
            status=status,
            error=out.get("error"),
            message=out.get("message") if status != "ok" else None,
            result=out if status == "ok" else None,  # what the agent got back (tests may check it: tool_results)
            attempts=attempts,  # 0 when a gate refused the call, otherwise how many tries it took, failed ones too
            idempotency_key=key,
            tool_kind=spec.kind if spec else None,
            agent=agent.name,
            duration_ms=round((time.perf_counter() - t0) * 1000, 3),
        )
        return out

    def _needs_approval(self, spec, name: str) -> bool:
        """True for a guarded tool that the configuration lists under ``tools.requires_approval``."""
        gated = self.config.get("tools.requires_approval") or []
        return spec.kind == "guarded" and name in gated


def _argument_error(spec, args: dict) -> str | None:
    """Why ``args`` do not fit the adapter signature (the agent's mistake), or None. Checked before the
    call so that a TypeError raised *inside* a tool is reported as a crash, not as bad arguments."""
    try:
        # bind() checks names and counts against the signature without calling anything; None stands in
        # for the ToolContext that the dispatcher itself passes as the first argument.
        inspect.signature(spec.fn).bind(None, **args)
    except TypeError as exc:
        return str(exc)
    return None
