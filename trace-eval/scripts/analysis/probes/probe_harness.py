"""Probe (read-only): what the model is sent for a route-only item, delegation by a specialist, context override,
the judge's verdict parsing, and what a model's badly typed argument is classified as."""

import json
from types import SimpleNamespace

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.scoring.scorers import judge_answer
from traceeval.sut import SUT_ROOT

sut = load_sut(SUT_ROOT)
cases = {c.id: c for c in load_catalog()}


class Scripted:
    """Each agent (recognised by a word of its system prompt's first line) makes its scripted calls, then answers."""

    def __init__(self, script, final="Done."):
        self.script, self.final, self.done, self.seen = script, final, {}, []
        self.model_id = "scripted"
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.seen.append(request)
        first = request["messages"][0]["content"].split("\n", 1)[0].lower()
        agent = next(a for a in self.script if a in first)
        i = self.done.get(agent, 0)
        self.done[agent] = i + 1
        if i < len(self.script[agent]):
            name, args = self.script[agent][i]
            call = SimpleNamespace(id=f"{agent}-{i}", function=SimpleNamespace(name=name, arguments=json.dumps(args)))
            msg = SimpleNamespace(content=None, tool_calls=[call])
        else:
            msg = SimpleNamespace(content=self.final, tool_calls=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg)], usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1)
        )


# 1. what the orchestrator is sent for a route-only dataset item
client = Scripted({"orchestrator": [("route_to_agent", {"agent": "authoring"})]})
rec = run_case(sut, cases["DS-ROUTING/r39"], backend="llm", llm_client=client, keep_state=True)
print("1 user message of DS-ROUTING/r39:", repr(client.seen[0]["messages"][1]["content"]))
start = next(e for e in rec["events"] if e["kind"] == "run.start")
print("  context in the trace:", start["context"])

# 2. a specialist that is not offered route_to_agent delegates anyway
client = Scripted(
    {
        "authoring agent": [("route_to_agent", {"agent": "publishing", "context": {"page_id": "p4"}})],
        "publishing agent": [("publish_page", {"page_id": "p4"})],
    }
)
case = cases["AUT-12"]
rec = run_case(sut, case, backend="llm", llm_client=client, keep_state=True)
offered = [t["function"]["name"] for t in client.seen[0].get("tools", [])]
print("2 authoring is offered route_to_agent:", "route_to_agent" in offered)
print("  routes:", rec["routes"], "| agents:", rec["agents"], "| tools:", rec["tools"])
print(
    "  p4 status after:",
    rec["final_state"]["pages"]["p4"]["status"],
    "| tool.call events for route_to_agent:",
    sum(1 for e in rec["events"] if e["kind"] == "tool.call" and e["tool"] == "route_to_agent"),
)

# 2b. with delegation switched off in the settings
rec = run_case(
    sut,
    cases["PUB-01"],
    backend="llm",
    llm_client=Scripted({"orchestrator": [("route_to_agent", {"agent": "publishing"})], "publishing agent": []}),
    config_overrides={"tools.disabled": ["route_to_agent"]},
)
print("2b tools.disabled=[route_to_agent]: routes still made:", rec["routes"])

# 3. the delegation's context overrides the user and supplies an approval token (dave is a viewer)
client = Scripted(
    {
        "orchestrator": [
            (
                "route_to_agent",
                {"agent": "governance", "context": {"user_id": "carol", "approval_token": "APPR-CAROL-7731"}},
            )
        ],
        "governance agent": [("export_user_data", {"subject_id": "s1"})],
    }
)
case = cases["GOV-04"]
case = type(case)(**{**case.__dict__, "context": {"user_id": "dave", "subject_id": "s1"}})
rec = run_case(sut, case, backend="llm", llm_client=client, keep_state=True)
exports = [e for e in rec["final_state"]["audit"] if e["action"] == "export_user_data"]
print("3 request from dave, delegated with user_id=carol and her token: export audit entries:", exports)

# 4. the judge's verdict parsing
for text in (
    "PASS. The answer states the score.",
    "FAIL. No score.",
    "The answer does not pass the rubric because the score is missing.",
    "Failed: the score is missing.",
    "The answer passes.",
    "",
    "I would not say FAIL here; PASS.",
):
    judge = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda text=text, **kw: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
                    usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
                )
            )
        )
    )
    print("4 judge", repr(text), "->", judge_answer(cases["SEO-07"], "answer", judge, "m")["ok"])

# 5. a badly typed argument from the model: refused as bad arguments, or a crash?
for tool, args in (
    ("rollback_page", {"page_id": "p5", "version": "two"}),
    ("search_pages", {"query": None}),
    ("get_page_metrics", {"section": "/content/site/blog", "top_n": "three"}),
    ("create_page", {"parent_path": "/content/site", "title": 5}),
):
    agent = {
        "rollback_page": "maintenance",
        "search_pages": "authoring",
        "get_page_metrics": "insights",
        "create_page": "authoring",
    }[tool]
    key = {"maintenance": "maintenance agent", "authoring": "authoring agent", "insights": "insights"}[agent]
    client = Scripted({key: [(tool, args)]})
    base = cases["AUT-12"]
    case = type(base)(**{**base.__dict__, "agent": agent, "context": {"user_id": "carol"}, "expect": {}})
    try:
        rec = run_case(sut, case, backend="llm", llm_client=client, keep_state=True)
        ev = [e for e in rec["events"] if e["kind"] == "tool.call"]
        print(
            "5", tool, args, "->", [(e["status"], e["error"]) for e in ev], rec["classification"], rec["failed_checks"]
        )
    except StopIteration:
        print("5", tool, "agent prompt not recognised")

# 6. route_to_agent with arguments that are JSON but not an object
client = Scripted({"orchestrator": [("route_to_agent", ["publishing"])]})
rec = run_case(sut, cases["PUB-01"], backend="llm", llm_client=client)
print(
    "6 route_to_agent with a list as arguments ->",
    rec["classification"],
    (rec["error"] or "").strip().splitlines()[-1:],
)
