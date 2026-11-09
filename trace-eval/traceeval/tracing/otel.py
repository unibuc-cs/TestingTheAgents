"""OpenTelemetry export of a run's trace, as one OTLP/JSON document.

``to_otlp`` turns the trace of one run into the JSON form of an OTLP ``ExportTraceServiceRequest``, the document an
OpenTelemetry collector accepts on ``/v1/traces`` and trace viewers import. It reads the trace document
(``TraceRecorder.to_dict()``) or a run record kept with ``keep_state=True`` (``experiment/executor.py::run_case``):
both carry the ``events``. It is built from plain dicts and ``json``, without the opentelemetry packages.

Spans, named and tagged after the OpenTelemetry GenAI semantic conventions where they fit:

    run <test id>          the root: from ``run.start`` to ``run.end``; test, run id, variant, backend, request,
                           termination, steps, token totals, config keys read
    invoke_agent <agent>   one per agent turn, from ``agent.start`` to its ``agent.end``; a delegated agent's span
                           is a child of the delegating agent's span; tokens of the agent's own model calls
    execute_tool <tool>    one per tool call, child of the calling agent's span; ``error.type`` when the call was
                           refused or crashed, status ERROR when it crashed
    chat                   one per model call, child of the agent's span, with its tokens; zero duration, since
                           the trace records only when the answer came back
    load_skill <skill>     one per skill load, an instant span under the agent's span

The "cognition events" are span events on the agent span: ``plan`` (a ``make_plan`` call: goal and steps),
``route`` (each delegation, accepted or refused), ``approval`` (a ``request_approval`` call: approved or not, by
whom) and ``consult`` (the specialist definitions an orchestrator read to choose).

Times: the recorder's ``t`` is seconds since the recorder started; the wall-clock ``started_at`` (epoch seconds)
is the origin. Ids come from a sha256 digest of the run id and the index of the event that opens the span, never
from a random source, so the same trace always gives the same document.
"""

import hashlib
import json
from pathlib import Path

from .. import __version__

SERVICE_NAME = "contentops"  # the application under test (docs/CONTENTOPS.md)
SCOPE_NAME = "traceeval.tracing.otel"
SPAN_KIND_INTERNAL = 1  # OTLP enums are written as integers in JSON
STATUS_ERROR = 2


def _hex_id(run_id: str, key: str, length: int) -> str:
    """A ``length``-character hex id: the start of the sha256 digest of the run id and ``key``."""
    return hashlib.sha256(f"{run_id}#{key}".encode()).hexdigest()[:length]


def _value(v) -> dict:
    """An attribute value in OTLP's AnyValue form. Lists of plain values become arrays; dicts and anything else
    become JSON text."""
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}  # an int64, written as a string like the times
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list | tuple) and all(isinstance(x, str | int | float | bool) for x in v):
        return {"arrayValue": {"values": [_value(x) for x in v]}}
    return {"stringValue": json.dumps(v, sort_keys=True, default=str)}


def _attributes(attrs: dict) -> list[dict]:
    """OTLP key-value pairs; attributes whose value is None are left out."""
    return [{"key": k, "value": _value(v)} for k, v in attrs.items() if v is not None]


class _Span:
    """A span while the events are read; ``to_otlp`` writes it out at the end."""

    def __init__(self, key: str, name: str, parent, start: float, attrs: dict, agent: str | None = None):
        self.key = key  # the index of the event that opened the span ("run" for the root); its id comes from it
        self.name = name
        self.parent = parent
        self.start = start
        self.end = start  # instant spans keep it
        self.attrs = attrs
        self.events: list[tuple[float, str, dict]] = []  # (t, name, attributes)
        self.status: dict | None = None
        self.agent = agent  # set on agent turns only
        self.input_tokens = 0  # an agent turn's own model calls
        self.output_tokens = 0


def to_otlp(trace: dict, started_at: float | None = None) -> dict:
    """The trace of one run as an OTLP/JSON document (``resourceSpans``).

    ``trace`` is ``TraceRecorder.to_dict()`` or a run record kept with ``keep_state=True``. ``started_at`` is the
    wall-clock time (epoch seconds) the recorder started; by default the trace's own ``started_at``, and 0 when it
    has none."""
    events = trace.get("events")
    if events is None:
        raise ValueError("the trace has no events: export TraceRecorder.to_dict() or a record kept with keep_state")
    origin = started_at if started_at is not None else (trace.get("started_at") or 0.0)
    test_id = trace.get("test_id", "")
    # The executor names runs "<variant>:<test id>:<repetition>"; a record without the name gets the same one.
    run_id = trace.get("run_id") or f"{trace.get('variant', 'baseline')}:{test_id}:{trace.get('rep', 0)}"
    last_t = max((e.get("t", 0.0) for e in events), default=0.0)

    start = next((e for e in events if e["kind"] == "run.start"), None)
    end = next((e for e in reversed(events) if e["kind"] == "run.end"), None)
    run = _Span("run", f"run {test_id}".strip(), None, start["t"] if start else 0.0, {})
    spans = [run]
    open_turns: list[_Span] = []  # the agent turns under way, the innermost last

    def current() -> _Span:
        return open_turns[-1] if open_turns else run

    def turn_of(agent) -> _Span:
        """The innermost open turn of ``agent``; the innermost turn of any agent if none matches."""
        return next((s for s in reversed(open_turns) if s.agent == agent), current())

    def child(i: int, name: str, parent: _Span, t: float, attrs: dict, agent: str | None = None) -> _Span:
        span = _Span(str(i), name, parent, t, attrs, agent)
        spans.append(span)
        return span

    for i, e in enumerate(events):
        kind, t = e["kind"], e.get("t", 0.0)
        if kind == "agent.start":
            attrs = {
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": e.get("agent"),
                "traceeval.agent.version": e.get("version"),
                "traceeval.agent.digest": e.get("digest"),
                "traceeval.agent.depth": e.get("depth"),
            }
            agent = e.get("agent")
            open_turns.append(child(i, f"invoke_agent {agent}", current(), t, attrs, agent=agent))
        elif kind == "agent.end":
            # Close the turn of this agent (and any inner turn left open, which a correct run never has).
            while open_turns:
                span = open_turns.pop()
                span.end = t
                if span.agent == e.get("agent"):
                    span.attrs["traceeval.agent.message"] = e.get("message")
                    break
        elif kind == "tool.call":
            parent = turn_of(e.get("agent"))
            tool, status, result = e.get("tool"), e.get("status"), e.get("result")
            attrs = {
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": tool,
                "gen_ai.agent.name": e.get("agent"),
                "gen_ai.tool.call.arguments": json.dumps(e.get("args"), sort_keys=True, default=str),
                "gen_ai.tool.call.result": None if result is None else json.dumps(result, sort_keys=True, default=str),
                "error.type": (e.get("error") or "tool_error") if status != "ok" else None,
                "traceeval.tool.status": status,
                "traceeval.tool.message": e.get("message"),
                "traceeval.tool.kind": e.get("tool_kind"),
                "traceeval.tool.attempts": e.get("attempts"),
                "traceeval.tool.idempotency_key": e.get("idempotency_key"),
            }
            # The event is written when the call returns: it ends the span, and the duration gives the start.
            span = child(i, f"execute_tool {tool}", parent, t - (e.get("duration_ms") or 0.0) / 1000, attrs)
            span.end = t
            if status == "crash":
                span.status = {"code": STATUS_ERROR, "message": e.get("message") or "tool crash"}
            args = e.get("args") if isinstance(e.get("args"), dict) else {}
            if tool == "make_plan":
                plan = {"goal": args.get("goal"), "steps": args.get("steps"), "status": status}
                parent.events.append((t, "plan", plan))
            elif tool == "request_approval":
                answer = result or {}  # a refused call has no answer: nothing was approved
                approval = {
                    "approved": bool(answer.get("approved")),
                    "approver": answer.get("approver"),
                    "summary": args.get("summary"),
                    "status": status,
                }
                parent.events.append((t, "approval", approval))
        elif kind == "llm.call":
            parent = turn_of(e.get("agent"))
            p, c = e.get("prompt_tokens", 0), e.get("completion_tokens", 0)
            attrs = {
                "gen_ai.operation.name": "chat",
                "gen_ai.agent.name": e.get("agent"),
                "gen_ai.usage.input_tokens": p,
                "gen_ai.usage.output_tokens": c,
            }
            child(i, "chat", parent, t, attrs)
            parent.input_tokens += p
            parent.output_tokens += c
        elif kind == "skill.load":
            # The loader reports a skill each time it is asked for it, and an agent turn asks twice (once to list
            # its skills, once to write out the entry skill's procedure): one span per skill and turn is enough.
            span = current()
            if any(s.parent is span and s.name == f"load_skill {e.get('skill')}" for s in spans):
                continue
            attrs = {
                "gen_ai.skill.name": e.get("skill"),
                "gen_ai.skill.version": e.get("version"),
                "gen_ai.skill.digest": e.get("digest"),
                "traceeval.skill.tokens": e.get("tokens"),
            }
            child(i, f"load_skill {e.get('skill')}", span, t, attrs)
        elif kind == "agent.route":
            route = {
                "target": e.get("target"),
                "status": e.get("status"),
                "reason": e.get("reason"),
                "task": e.get("task"),
                "context": e.get("context"),
            }
            turn_of(e.get("source")).events.append((t, "route", route))
        elif kind == "agent.consult":
            # An orchestrator reads every specialist's definition in a row: one event lists them all.
            span = current()
            if span.events and span.events[-1][1] == "consult":
                span.events[-1][2]["agents"].append(e.get("agent"))
            else:
                span.events.append((t, "consult", {"agents": [e.get("agent")], "fields": e.get("fields", [])}))

    # A run that broke off leaves turns open: they end with the last event and are marked as errors.
    for span in open_turns:
        span.end = last_t
        span.status = {"code": STATUS_ERROR, "message": "the agent's turn did not end"}
    run.end = end["t"] if end else last_t
    tokens_in = sum(e.get("prompt_tokens", 0) for e in events if e["kind"] == "llm.call")
    tokens_out = sum(e.get("completion_tokens", 0) for e in events if e["kind"] == "llm.call")
    end = end or {}
    start = start or {}
    run.attrs = {
        "traceeval.test_id": test_id,
        "traceeval.run_id": run_id,
        "traceeval.variant": trace.get("variant"),
        "traceeval.backend": trace.get("backend"),
        "traceeval.entry_agent": start.get("agent"),
        "traceeval.request": start.get("request"),
        "traceeval.context": start.get("context"),
        "traceeval.termination": end.get("termination"),
        "traceeval.steps": end.get("steps"),
        "traceeval.final_message": end.get("message"),
        "gen_ai.usage.input_tokens": end.get("prompt_tokens", tokens_in),
        "gen_ai.usage.output_tokens": end.get("completion_tokens", tokens_out),
        "traceeval.config_keys": sorted({e["key"] for e in events if e["kind"] == "config.read"}),
    }
    error = trace.get("error")  # a run record's harness error (a traceback), if any
    if not end or error:
        message = error.strip().splitlines()[-1] if error else "the run ended without a run.end event"
        run.status = {"code": STATUS_ERROR, "message": message}

    trace_id = _hex_id(run_id, "trace", 32)

    def ns(t: float) -> str:
        return str(round(origin * 1e9) + round(t * 1e9))

    def write(span: _Span) -> dict:
        attrs = dict(span.attrs)
        if span.agent is not None:
            attrs["gen_ai.usage.input_tokens"] = span.input_tokens
            attrs["gen_ai.usage.output_tokens"] = span.output_tokens
        out = {
            "traceId": trace_id,
            "spanId": _hex_id(run_id, span.key, 16),
            "name": span.name,
            "kind": SPAN_KIND_INTERNAL,
            "startTimeUnixNano": ns(span.start),
            "endTimeUnixNano": ns(span.end),
            "attributes": _attributes(attrs),
        }
        if span.parent is not None:
            out["parentSpanId"] = _hex_id(run_id, span.parent.key, 16)
        if span.events:
            out["events"] = [
                {"timeUnixNano": ns(t), "name": name, "attributes": _attributes(a)} for t, name, a in span.events
            ]
        if span.status:
            out["status"] = span.status
        return out

    resource = {"attributes": _attributes({"service.name": SERVICE_NAME})}
    scope_spans = {"scope": {"name": SCOPE_NAME, "version": __version__}, "spans": [write(s) for s in spans]}
    return {"resourceSpans": [{"resource": resource, "scopeSpans": [scope_spans]}]}


def write_otlp(path, trace: dict, started_at: float | None = None) -> Path:
    """Write ``to_otlp(trace, started_at)`` to ``path`` as JSON and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_otlp(trace, started_at), indent=1))
    return path
