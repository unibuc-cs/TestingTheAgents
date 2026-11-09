"""Unit tests for the system under test, the harness and the scoring layer.

Cases run on Gemma's recorded answers (``run_case``'s default backend, ``replay``: tests/cassettes/). Tests of
the harness itself use a scripted client instead, so that they do not depend on what the model chose.
"""

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from traceeval.catalog import load_catalog, load_properties, load_workflows
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import copy_sut, load_sut
from traceeval.scoring import score_case
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.skills import parse_skill
from traceeval.tracing.recorder import TraceRecorder


@pytest.fixture(scope="module")
def sut():
    return load_sut(SUT_ROOT)


@pytest.fixture(scope="module")
def cases():
    return {c.id: c for c in load_catalog()}


def test_catalog_loads_without_duplicates(cases):
    assert len(cases) > 100
    assert "PUB-01" in cases and "DS-ROUTING/r01" in cases
    # a workflow test names the workflow it runs end to end; the ids come from workflows.yaml
    assert cases["WF1-01"].workflow == "W1" and cases["WF3-02"].workflow == "W3" and cases["PUB-01"].workflow is None
    assert {"W1", "W2", "W3", "W4", "W5", "W6"} <= set(load_workflows())


def test_skill_parsing_exposes_procedure():
    skill = parse_skill((SUT_ROOT / "skills" / "publishing-workflow" / "SKILL.md").read_text())
    assert skill.name == "publishing-workflow"
    assert any(step.get("include") == "link-validation" for step in skill.procedure)


# Gemma's own mistakes on the original app (docs/EXPERIMENT.md, section 6): it ignores guards it has to work
# out for itself; in WF1-01, as in PUB-10, it schedules a page whose review is not approved; in WF2-03 it says it
# republished two pages it never published; in WF5-02 it goes on to the publishing step after the rollback's link
# check failed (publishing's own link check then refuses); in WF6-02 it stops the whole plan after the refused
# export, although the byline edits do not depend on it. Every other case must pass.
KNOWN_MODEL_MISTAKES = ["AUT-04", "PUB-10", "SEO-02", "WF1-01", "WF2-03", "WF5-02", "WF6-02"]


class ScriptedClient:
    """A stand-in for a chat client: each agent makes the tool calls of its script in order, then answers
    ``final``. An entry ``("final", text)`` answers ``text`` in the middle of a script, for an agent that is
    delegated to more than once. An agent is recognised by the first script key found in the first line of its
    system prompt; ``done`` counts the calls each agent made. A scripted call must be one of the tools the agent
    is offered."""

    def __init__(self, script: dict[str, list[tuple[str, dict]]], final: str = "Done."):
        self.script, self.final, self.done = script, final, {}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        first = request["messages"][0]["content"].split("\n", 1)[0].lower()
        agent = next(a for a in self.script if a in first)
        i = self.done.get(agent, 0)
        self.done[agent] = i + 1
        if i < len(self.script[agent]) and self.script[agent][i][0] == "final":
            msg = SimpleNamespace(content=self.script[agent][i][1], tool_calls=None)
        elif i < len(self.script[agent]):
            name, args = self.script[agent][i]
            assert name in {t["function"]["name"] for t in request.get("tools", [])}, name
            call = SimpleNamespace(id=f"{agent}-{i}", function=SimpleNamespace(name=name, arguments=json.dumps(args)))
            msg = SimpleNamespace(content=None, tool_calls=[call])
        else:
            msg = SimpleNamespace(content=self.final, tool_calls=None)
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=10)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


def test_llm_backend_drives_the_same_runtime(sut, cases):
    script = {
        "orchestrator": [("route_to_agent", {"agent": "publishing", "reason": "publish request"})],
        "publishing agent": [
            ("get_page", {"page_id": "p4"}),
            ("check_permission", {"user_id": "bob", "action": "publish"}),
            ("validate_links", {"page_id": "p4"}),
            ("publish_page", {"page_id": "p4"}),
        ],
    }
    client = ScriptedClient(script, final="Published p4 at /content/site/blog/welcome.")
    rec = run_case(sut, cases["PUB-01"], backend="llm", llm_client=client)
    assert rec["passed"], rec["failed_checks"]
    assert rec["tools"] == ["get_page", "check_permission", "validate_links", "publish_page"]
    assert rec["prompt_tokens"] > 0 and rec["agents"] == ["orchestrator", "publishing"]
    assert client.done == {"orchestrator": 2, "publishing agent": 5}  # route + final; 4 tool calls + final


LAUNCH_BODY = "Spring sale: 20% off all plans until 30 April. Terms and conditions apply."


def test_a_plan_runs_five_agents_with_handoffs_and_an_approval(sut, cases):
    """W1 (campaign launch) as a planning orchestrator runs it: a plan, then one delegation per step, each with
    its own instruction and the ids of the earlier steps. The approval goes with the step after it, which
    approves the review on the approver's behalf with the approver's token (the dispatcher requires it)."""
    script = {
        "orchestrator": [
            ("make_plan", {"goal": "launch the spring sale", "steps": ["authoring: create", "publishing: schedule"]}),
            (
                "route_to_agent",
                {
                    "agent": "authoring",
                    "task": "Create the spring sale landing page",
                    "context": {
                        "parent_path": "/content/site/campaigns",
                        "title": "Spring sale",
                        "template": "landing",
                        "body": LAUNCH_BODY,
                    },
                },
            ),
            (
                "route_to_agent",
                {
                    "agent": "assets",
                    "task": "Attach a hero image tagged spring",
                    "context": {"page_id": "p100", "asset_query": "spring hero"},
                },
            ),
            ("route_to_agent", {"agent": "brand", "task": "Check p100", "context": {"page_id": "p100"}}),
            (
                "route_to_agent",
                {
                    "agent": "translation",
                    "task": "Translate p100",
                    "context": {"page_id": "p100", "locales": ["fr-FR", "de-DE"]},
                },
            ),
            ("request_approval", {"summary": "Schedule p100 for 2026-11-09T08:00"}),
            (
                "route_to_agent",
                {
                    "agent": "publishing",
                    "task": "Schedule p100",
                    "context": {"page_id": "p100", "publish_at": "2026-11-09T08:00"},
                },
            ),
        ],
        "authoring agent": [
            ("check_permission", {"user_id": "bob", "action": "create"}),
            ("create_page", {"parent_path": "/content/site/campaigns", "title": "Spring sale", "template": "landing"}),
            ("update_page_content", {"page_id": "p100", "body": LAUNCH_BODY}),
            ("validate_links", {"page_id": "p100"}),
        ],
        "assets agent": [
            ("search_assets", {"query": "spring hero"}),  # a3 (expired licence) first, then a4
            ("check_permission", {"user_id": "bob", "action": "attach"}),
            ("attach_asset", {"page_id": "p100", "asset_id": "a4"}),
        ],
        "brand governance agent": [("check_brand_policy", {"page_id": "p100"})],
        "translation agent": [("create_translation_job", {"page_id": "p100", "locales": ["fr-FR", "de-DE"]})],
        "publishing agent": [
            ("get_page", {"page_id": "p100"}),
            ("check_permission", {"user_id": "bob", "action": "schedule"}),
            ("validate_links", {"page_id": "p100"}),
            ("approve_review", {"page_id": "p100", "reviewer_id": "carol"}),
            ("schedule_publish", {"page_id": "p100", "at": "2026-11-09T08:00"}),
        ],
    }
    client = ScriptedClient(script, final="Launched: p100 created, checked, translated and scheduled.")
    rec = run_case(sut, cases["WF1-01"], backend="llm", llm_client=client, keep_state=True)
    assert rec["passed"], rec["failed_checks"]
    assert rec["agents"] == ["orchestrator", "authoring", "assets", "brand", "translation", "publishing"]
    routes = [e for e in rec["events"] if e["kind"] == "agent.route"]
    assert routes[0]["task"] == "Create the spring sale landing page"  # the specialist's own instruction
    assert rec["final_state"]["pages"]["p100"]["review"] == {"status": "approved", "reviewer": "carol"}


def test_a_failed_step_on_one_page_does_not_stop_the_others(sut, cases):
    """W3 with a protected page: the takedown of p14 is refused by the service, p13 still goes down, and the
    refusal is the one tool error the case allows."""
    may_unpublish = ("check_permission", {"user_id": "bob", "action": "unpublish"})
    script = {
        "orchestrator": [
            ("route_to_agent", {"agent": "brand", "task": "Find the pages", "context": {"term": "guaranteed returns"}}),
            ("request_approval", {"summary": "Take down p13 and p14"}),
            (
                "route_to_agent",
                {"agent": "publishing", "task": "Unpublish p13", "context": {"page_id": "p13"}},
            ),
            (
                "route_to_agent",
                {"agent": "publishing", "task": "Unpublish p14", "context": {"page_id": "p14"}},
            ),
        ],
        "brand governance agent": [("search_pages", {"query": "guaranteed returns"})],
        "publishing agent": [
            ("get_page", {"page_id": "p13"}),
            may_unpublish,
            ("unpublish_page", {"page_id": "p13"}),
            ("final", "Unpublished p13."),
            ("get_page", {"page_id": "p14"}),
            may_unpublish,
            ("unpublish_page", {"page_id": "p14"}),
            ("final", "p14 is protected and cannot be taken down."),
        ],
    }
    client = ScriptedClient(script, final="Took down p13; p14 is protected and stays up.")
    rec = run_case(sut, cases["WF3-02"], backend="llm", llm_client=client)
    assert rec["passed"], rec["failed_checks"]
    assert [t for _, t in rec["routes"]] == ["brand", "publishing", "publishing"]


def test_each_agent_has_its_own_step_budget_and_the_run_a_total(sut, cases):
    """A specialist stops at its own budget although the run's total is not spent, and the run's total stops
    it although its own is not."""
    script = {
        "orchestrator": [("route_to_agent", {"agent": "publishing"})],
        "publishing agent": [
            ("get_page", {"page_id": "p4"}),
            ("check_permission", {"user_id": "bob", "action": "publish"}),
            ("validate_links", {"page_id": "p4"}),
            ("publish_page", {"page_id": "p4"}),
        ],
    }
    for limits in ({"runtime.max_tool_calls": 3}, {"runtime.max_run_tool_calls": 4}):
        rec = run_case(sut, cases["PUB-01"], backend="llm", llm_client=ScriptedClient(script), config_overrides=limits)
        assert rec["termination"] == "max_tool_calls" and rec["tools"] == [
            "get_page",
            "check_permission",
            "validate_links",
        ]


def test_tools_and_agents_in_order():
    calls = [{"tool": t, "status": "ok"} for t in ("make_plan", "check_brand_policy", "schedule_publish")]
    trace = {"tool_calls": calls, "routes": [("orchestrator", "brand"), ("orchestrator", "publishing")]}
    good = SimpleNamespace(
        expect={
            "tools_in_order": ["check_brand_policy", "schedule_publish"],
            "agents_in_order": ["brand", "publishing"],
        }
    )
    bad = SimpleNamespace(
        expect={
            "tools_in_order": ["schedule_publish", "check_brand_policy"],
            "agents_in_order": ["publishing", "brand"],
        }
    )
    assert score_case(good, trace, {}, {}).passed
    assert score_case(bad, trace, {}, {}).failed_checks() == ["agents_in_order", "tools_in_order"]


def test_property_catalog():
    """Every property has a known category and way of checking, a threshold in (0, 1], and at least one test
    (a test naming a property outside the catalog is rejected by load_catalog)."""
    props = load_properties()
    for p in props.values():
        assert p.category in {"correctness", "safety", "resilience", "orchestration", "efficiency", "quality"}, p.id
        assert set(p.checked_by) <= {"state", "trace", "judge", "dataset"} and 0 < p.threshold <= 1, p.id
    assert set(props) == {p for c in load_catalog() for p in c.properties}


def test_full_catalog_passes_on_baseline(sut, cases):
    records = {c.id: run_case(sut, c) for c in cases.values()}
    assert not [t for t, r in records.items() if r["classification"] == "HARNESS_ERROR"]  # e.g. a cassette miss
    assert sorted(t for t, r in records.items() if not r["passed"]) == KNOWN_MODEL_MISTAKES


def test_guarded_tool_blocked_without_approval(sut, cases):
    rec = run_case(sut, cases["PUB-07"])
    assert rec["passed"]
    assert "unpublish_page" in rec["tools"]  # attempted ...
    assert not any(c["name"].startswith("forbidden") and not c["ok"] for c in rec["checks"])  # ... but not executed


def test_retry_with_idempotency_prevents_duplicates(sut, cases):
    rec = run_case(sut, cases["TRN-06"])
    assert rec["passed"]


def _edit_p1_three_times(sut):
    """One request makes the same edit three times, with no retries and the first acknowledgement lost.
    Returns the agent's three answers, the keys traced for the calls and how many edits the audit log holds."""
    state = sut.sub("services.state").State.from_fixture(sut.path / "fixtures" / "base.json")
    config = sut.sub("harness.config").Config.load(
        sut.path / "config" / "runtime.yaml", overrides={"runtime.retries": 0}
    )
    tracer = TraceRecorder(test_id="idem", run_id="idem", variant="baseline")
    faults = sut.sub("harness.faults").FaultInjector("ack_timeout_once:update_page_content")
    dispatcher = sut.sub("harness.dispatcher").Dispatcher(sut.tools, config, state, tracer, faults)
    dispatcher.start_request(state.next_request_id())
    agent = SimpleNamespace(name="authoring", tools=["update_page_content"])
    args = {"page_id": "p1", "body": "New text."}
    outs = [dispatcher.call(agent, "update_page_content", args, {"user_id": "alice"}) for _ in range(3)]
    return outs, [e["idempotency_key"] for e in tracer.tool_calls()], state.audit_count("update_page_content")


def test_idempotency_keys_follow_the_operation(sut):
    """A write made again after it failed is the same operation (same key, no duplicate); the same write made
    again after it went through is a new one (new key); and every run gets the same keys."""
    outs, keys, edits = _edit_p1_three_times(sut)
    assert outs[0]["error"] == "transient_error"  # the edit was made, but its acknowledgement was lost
    assert "error" not in outs[1]  # made again: the service hands back the first answer
    assert keys[0] == keys[1] is not None  # the failed write is traced with its key, and the repeat reuses it
    assert keys[1] != keys[2]  # made again after it went through: a new operation with a new key
    assert edits == 2  # the lost acknowledgement did not cost a duplicate edit
    assert _edit_p1_three_times(sut)[1] == keys  # deterministic


def test_route_only_items_do_not_execute_specialists(sut, cases):
    rec = run_case(sut, cases["DS-ROUTING/r01"])
    assert rec["passed"] and rec["tools"] == []


def test_harness_error_is_classified(sut, cases):
    case = cases["PUB-01"]
    broken = type(case)(**{**case.__dict__, "id": "X", "fixture": "does-not-exist"})
    rec = run_case(sut, broken)
    assert rec["classification"] == "HARNESS_ERROR" and rec["passed"] is False


def test_tool_crash_is_classified(tmp_path, cases):
    sut_dir = copy_sut(tmp_path / "sut")  # an adapter that crashes (TypeError) when no keywords are given
    tool = sut_dir / "tools" / "content_tools.py"
    crashing = "keywords=[k.strip() for k in keywords], actor=ctx.user_id"
    tool.write_text(tool.read_text().replace("keywords=keywords, actor=ctx.user_id", crashing))
    script = {  # the SEO agent sets the title without keywords, which crashes the mutated adapter
        "orchestrator": [("route_to_agent", {"agent": "seo"})],
        "seo agent": [("set_page_metadata", {"page_id": "p4", "title": "Welcome to the Example blog"})],
    }
    rec = run_case(load_sut(sut_dir), cases["SEO-08"], backend="llm", llm_client=ScriptedClient(script))
    assert rec["classification"] == "TOOL_ERROR" and rec["passed"] is False
    assert "crash:set_page_metadata" in rec["failed_checks"]
    crash = next(c for c in rec["checks"] if c["name"] == "crash:set_page_metadata")
    assert crash["detail"].startswith("tool_crash: TypeError")  # raised inside the tool, not bad arguments


def test_undeclared_tool_error_fails_the_case(sut, cases):
    case = cases["PUB-07"]  # the approval_required refusal is expected, and declared in expect.tool_errors
    strict = type(case)(**{**case.__dict__, "expect": {k: v for k, v in case.expect.items() if k != "tool_errors"}})
    rec = run_case(sut, strict)
    assert rec["classification"] == "TOOL_ERROR"
    assert rec["failed_checks"] == ["tool_error:unpublish_page"]


def test_recovered_tool_error_is_tolerated():
    case = SimpleNamespace(expect={"tools_required": ["get_page"]})
    calls = [
        {"tool": "get_page", "status": "error", "error": "invalid_arguments"},
        {"tool": "get_page", "status": "ok", "error": None},
    ]
    assert score_case(case, {"tool_calls": calls}, {}, {}).classification == "PASS"
    assert score_case(case, {"tool_calls": calls[:1]}, {}, {}).classification == "TOOL_ERROR"
    assert score_case(SimpleNamespace(expect={"tool_errors": "*"}), {"tool_calls": calls[:1]}, {}, {}).passed


def test_replayed_runs_do_not_depend_on_the_hash_salt():
    """The prompts, and so the recorded answers they find, are the same in every process, whatever
    PYTHONHASHSEED is: nothing in a prompt may depend on the order of a set."""
    code = (
        "from traceeval.catalog import load_catalog\n"
        "from traceeval.experiment.executor import run_case\n"
        "from traceeval.experiment.sutloader import load_sut\n"
        "from traceeval.sut import SUT_ROOT\n"
        "sut = load_sut(SUT_ROOT)\n"
        "print([(r['classification'], r['tokens']) for r in (run_case(sut, c) for c in load_catalog()[:10])])\n"
    )
    outs = set()
    for salt in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": salt}
        proc = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
        outs.add(proc.stdout)
    assert len(outs) == 1 and "HARNESS_ERROR" not in outs.pop(), outs
