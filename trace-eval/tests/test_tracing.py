"""Tests of the OpenTelemetry export (``traceeval/tracing/otel.py``).

Two cases run on Gemma's recorded answers (``replay``, no model): PUB-01, one delegation, and WF3-01, a planned
workflow (orchestrator -> brand -> publishing, with an approval in between). The tests check the span tree, the
cognition events, the token attributes and that the ids do not depend on when the run happened; a hand-written
trace checks how a refused call, a crashed call and a run that broke off are reported.
"""

import json

import pytest

from traceeval.catalog import load_catalog
from traceeval.cli import main
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.sut import SUT_ROOT
from traceeval.tracing import TraceRecorder
from traceeval.tracing.otel import to_otlp, write_otlp

STATUS_ERROR = 2


@pytest.fixture(scope="module")
def sut():
    return load_sut(SUT_ROOT)


@pytest.fixture(scope="module")
def cases():
    return {c.id: c for c in load_catalog()}


@pytest.fixture(scope="module")
def records(sut, cases):
    out = {tid: run_case(sut, cases[tid], backend="replay", keep_state=True) for tid in ("PUB-01", "WF3-01")}
    for tid, rec in out.items():
        assert rec["error"] is None and rec["passed"], f"{tid} must pass on the recorded answers: {rec['error']}"
    return out


def spans_of(doc: dict) -> list[dict]:
    (resource_spans,) = doc["resourceSpans"]
    (scope_spans,) = resource_spans["scopeSpans"]
    return scope_spans["spans"]


def _plain(value: dict):
    if "arrayValue" in value:
        return [_plain(v) for v in value["arrayValue"]["values"]]
    if "intValue" in value:
        return int(value["intValue"])
    (v,) = value.values()
    return v


def attrs(item: dict) -> dict:
    """The attributes of a span or a span event, as plain values."""
    return {a["key"]: _plain(a["value"]) for a in item.get("attributes", [])}


def by_operation(spans: list[dict], operation: str) -> list[dict]:
    return [s for s in spans if attrs(s).get("gen_ai.operation.name") == operation]


@pytest.mark.parametrize("tid", ["PUB-01", "WF3-01"])
def test_span_tree_follows_the_run(records, tid):
    rec = records[tid]
    spans = spans_of(to_otlp(rec))
    by_id = {s["spanId"]: s for s in spans}
    assert len(by_id) == len(spans), "span ids are unique"
    assert len({s["traceId"] for s in spans}) == 1 and len(spans[0]["traceId"]) == 32
    assert all(len(s["spanId"]) == 16 and int(s["spanId"], 16) for s in spans)

    # one root, the run, with the run's totals
    roots = [s for s in spans if "parentSpanId" not in s]
    assert [r["name"] for r in roots] == [f"run {tid}"]
    run = attrs(roots[0])
    assert run["traceeval.test_id"] == tid and run["traceeval.run_id"] == f"baseline:{tid}:0"
    assert run["traceeval.variant"] == "baseline" and run["traceeval.backend"] == "replay"
    assert run["traceeval.termination"] == rec["termination"] and run["traceeval.steps"] == rec["steps"]
    assert run["gen_ai.usage.input_tokens"] == rec["prompt_tokens"]
    assert run["gen_ai.usage.output_tokens"] == rec["completion_tokens"]

    # every parent exists and every span lies inside its parent (a microsecond of rounding allowed)
    for s in spans:
        assert int(s["startTimeUnixNano"]) <= int(s["endTimeUnixNano"])
        if "parentSpanId" in s:
            parent = by_id[s["parentSpanId"]]
            assert int(s["startTimeUnixNano"]) >= int(parent["startTimeUnixNano"]) - 1000
            assert int(s["endTimeUnixNano"]) <= int(parent["endTimeUnixNano"]) + 1000

    # agent turns: one per agent.start, nested by delegation
    agents = by_operation(spans, "invoke_agent")
    starts = [e for e in rec["events"] if e["kind"] == "agent.start"]
    assert [attrs(a)["gen_ai.agent.name"] for a in agents] == [e["agent"] for e in starts]
    for a in agents:
        depth, parent = attrs(a)["traceeval.agent.depth"], by_id[a["parentSpanId"]]
        if depth == 0:
            assert parent is roots[0]
        else:
            assert attrs(parent)["gen_ai.operation.name"] == "invoke_agent"
            assert attrs(parent)["traceeval.agent.depth"] == depth - 1

    # tool calls and model calls: under the turn of the agent that made them
    tools = by_operation(spans, "execute_tool")
    assert [attrs(s)["gen_ai.tool.name"] for s in tools] == rec["tools"]
    chats = by_operation(spans, "chat")
    assert len(chats) == sum(e["kind"] == "llm.call" for e in rec["events"])
    for s in tools + chats:
        parent = attrs(by_id[s["parentSpanId"]])
        assert parent["gen_ai.operation.name"] == "invoke_agent"
        assert parent["gen_ai.agent.name"] == attrs(s)["gen_ai.agent.name"]
    assert all(s["startTimeUnixNano"] == s["endTimeUnixNano"] for s in chats)
    assert sum(attrs(s)["gen_ai.usage.input_tokens"] for s in chats) == rec["prompt_tokens"]
    assert sum(attrs(s)["gen_ai.usage.output_tokens"] for s in agents) == rec["completion_tokens"]

    # skill loads: instant spans under an agent turn
    skills = [s for s in spans if s["name"].startswith("load_skill ")]
    assert {attrs(s)["gen_ai.skill.name"] for s in skills} == set(rec["skills"])
    assert all(attrs(s)["gen_ai.skill.version"] and attrs(s)["gen_ai.skill.digest"] for s in skills)


def test_planned_workflow_has_its_cognition_events(records):
    spans = spans_of(to_otlp(records["WF3-01"]))
    by_id = {s["spanId"]: s for s in spans}
    agents = by_operation(spans, "invoke_agent")
    (orch,) = [a for a in agents if attrs(a)["gen_ai.agent.name"] == "orchestrator"]
    children = [attrs(a)["gen_ai.agent.name"] for a in agents if a.get("parentSpanId") == orch["spanId"]]
    assert children == ["brand", "publishing"]

    names = [e["name"] for e in orch["events"]]
    assert names[0] == "consult" and {"plan", "route", "approval"} <= set(names)
    consulted = attrs(orch["events"][0])
    assert {"brand", "publishing"} <= set(consulted["agents"]) and "orchestrator" not in consulted["agents"]
    plan = attrs(orch["events"][names.index("plan")])
    assert plan["goal"] and len(plan["steps"]) >= 2
    routes = [attrs(e) for e in orch["events"] if e["name"] == "route"]
    assert [r["target"] for r in routes if r["status"] == "ok"] == ["brand", "publishing"]
    approval = attrs(orch["events"][names.index("approval")])
    assert approval["approved"] is True and approval["approver"]
    # the plan comes first, the approval between the delegation to brand and the one to publishing
    route_at = [i for i, n in enumerate(names) if n == "route"]
    assert names.index("plan") < route_at[0] < names.index("approval") < route_at[-1]
    # the specialists made no delegation of their own
    assert all("events" not in a for a in agents if a is not orch)

    def tools_of(agent):
        return [
            attrs(s)["gen_ai.tool.name"]
            for s in by_operation(spans, "execute_tool")
            if attrs(by_id[s["parentSpanId"]])["gen_ai.agent.name"] == agent
        ]

    assert tools_of("orchestrator") == ["make_plan", "request_approval"]
    assert tools_of("brand") == ["search_pages"]
    assert set(tools_of("publishing")) == {"unpublish_page"}


def test_export_is_deterministic(sut, cases, records, tmp_path):
    rec = records["PUB-01"]
    assert to_otlp(rec) == to_otlp(rec)
    path = write_otlp(tmp_path / "otel" / "pub01.json", rec)
    assert json.loads(path.read_text()) == to_otlp(rec)

    # a second run of the case: other times, the same ids and the same tree
    again = run_case(sut, cases["PUB-01"], backend="replay", keep_state=True)

    def shape(r):
        return [(s["traceId"], s["spanId"], s.get("parentSpanId"), s["name"]) for s in spans_of(to_otlp(r))]

    assert shape(again) == shape(rec)
    # another run id, another trace
    assert spans_of(to_otlp({**rec, "run_id": "baseline:PUB-01:1"}))[0]["traceId"] != shape(rec)[0][0]

    # the time origin: the record's wall-clock start by default, or the one given
    run_start = next(e["t"] for e in rec["events"] if e["kind"] == "run.start")
    assert spans_of(to_otlp(rec, started_at=0))[0]["startTimeUnixNano"] == str(round(run_start * 1e9))
    default = int(spans_of(to_otlp(rec))[0]["startTimeUnixNano"])
    assert default == round(rec["started_at"] * 1e9) + round(run_start * 1e9)


def test_refused_and_crashed_calls_and_a_broken_run():
    tracer = TraceRecorder(test_id="T", run_id="baseline:T:0", variant="baseline", backend="replay")
    tracer.event("run.start", agent="publishing", request="publish p1", context={"user_id": "bob"})
    tracer.event("agent.start", agent="publishing", version="1", digest="abc", depth=0)
    common = {"result": None, "attempts": 1, "idempotency_key": None, "agent": "publishing", "duration_ms": 0.0}
    refusal = {"tool": "get_page", "status": "error", "error": "not_found", "message": "no page p9"}
    crash = {"tool": "publish_page", "status": "crash", "error": "tool_crash", "message": "KeyError: 'status'"}
    tracer.event("tool.call", args={"page_id": "p9"}, tool_kind="read", **refusal, **common)
    tracer.event("tool.call", args={"page_id": "p1"}, tool_kind="guarded", **crash, **common)
    # no agent.end and no run.end: the run broke off
    spans = spans_of(to_otlp(tracer.to_dict()))
    run, agent, refused, crashed = spans
    assert attrs(refused)["error.type"] == "not_found" and "status" not in refused
    assert attrs(crashed)["error.type"] == "tool_crash"
    assert crashed["status"] == {"code": STATUS_ERROR, "message": "KeyError: 'status'"}
    assert agent["status"]["code"] == STATUS_ERROR and run["status"]["code"] == STATUS_ERROR
    assert agent["endTimeUnixNano"] == run["endTimeUnixNano"] == crashed["endTimeUnixNano"]
    with pytest.raises(ValueError):
        to_otlp({"test_id": "T"})  # a history record has no events to export


def test_cli_run_writes_the_otlp_document(tmp_path, capsys):
    out = tmp_path / "trace.json"
    main(["run", "--test", "PUB-01", "--backend", "replay", "--otel", str(out)])
    printed = json.loads(capsys.readouterr().out)
    assert printed["passed"] and "events" not in printed and "final_state" not in printed
    spans = spans_of(json.loads(out.read_text()))
    assert spans[0]["name"] == "run PUB-01"
    agents = [attrs(s)["gen_ai.agent.name"] for s in by_operation(spans, "invoke_agent")]
    assert agents == ["orchestrator", "publishing"]
