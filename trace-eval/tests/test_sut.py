"""Unit tests for the system under test, the harness and the scoring layer."""

import pytest

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.expressions import DotDict, resolve_value, safe_eval
from traceeval.sut.harness.router import detect_intent, route
from traceeval.sut.harness.skills import parse_skill


@pytest.fixture(scope="module")
def sut():
    return load_sut(SUT_ROOT)


@pytest.fixture(scope="module")
def cases():
    return {c.id: c for c in load_catalog()}


def test_catalog_loads_without_duplicates(cases):
    assert len(cases) > 100
    assert "PUB-01" in cases and "DS-ROUTING/r01" in cases


def test_safe_eval_whitelist():
    env = {"last": DotDict({"allowed": True, "broken": [{"link": "x"}]}), "ctx": {"page_id": "p1"}}
    assert safe_eval("last.allowed", env) is True
    assert safe_eval("[b['link'] for b in last.broken]", env) == ["x"]
    assert resolve_value("$page_id", env) == "p1"
    with pytest.raises(ValueError):
        safe_eval("__import__('os').system('true')", env)


def test_skill_parsing_exposes_procedure():
    skill = parse_skill((SUT_ROOT / "skills" / "publishing-workflow" / "SKILL.md").read_text())
    assert skill.name == "publishing-workflow"
    assert any(step.get("include") == "link-validation" for step in skill.procedure)


def test_router_prefers_phrase_triggers(sut):
    agents = sut.sub("harness.agents").AgentLoader(SUT_ROOT / "agents").load_all()
    target, info = route("Take it down, the update was wrong", agents, "authoring")
    assert target == "publishing" and info["reason"] == "trigger_match"
    assert route("Hello there", agents, "authoring")[0] == "authoring"
    assert detect_intent("Take down the old news page", agents["publishing"].intents) == "unpublish"


def test_full_catalog_passes_on_baseline(sut, cases):
    failures = [c.id for c in cases.values() if not run_case(sut, c)["passed"]]
    assert failures == []


def test_guarded_tool_blocked_without_approval(sut, cases):
    rec = run_case(sut, cases["PUB-07"])
    assert rec["passed"]
    assert "unpublish_page" in rec["tools"]  # attempted ...
    assert not any(c["name"].startswith("forbidden") and not c["ok"] for c in rec["checks"])  # ... but not executed


def test_retry_with_idempotency_prevents_duplicates(sut, cases):
    rec = run_case(sut, cases["TRN-06"])
    assert rec["passed"]


def test_route_only_items_do_not_execute_specialists(sut, cases):
    rec = run_case(sut, cases["DS-ROUTING/r01"])
    assert rec["passed"] and rec["tools"] == []


def test_harness_error_is_classified(sut, cases):
    case = cases["PUB-01"]
    broken = type(case)(**{**case.__dict__, "id": "X", "fixture": "does-not-exist"})
    rec = run_case(sut, broken)
    assert rec["classification"] == "HARNESS_ERROR" and rec["passed"] is False
