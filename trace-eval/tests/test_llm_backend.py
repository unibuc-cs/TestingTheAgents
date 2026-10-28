"""The LLM backend against a scripted stand-in for an OpenAI-compatible client."""

import json
from types import SimpleNamespace

from traceeval.catalog import load_catalog
from traceeval.experiment.executor import run_case
from traceeval.experiment.sutloader import load_sut
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.backends.llm_openai import LLMSettings


class FakeCompletions:
    """Replies with scripted tool calls depending on which agent's system prompt it sees."""

    def __init__(self):
        self.calls = 0
        self.script = {
            "orchestrator": [("route_to_agent", {"agent": "publishing", "reason": "publish request"})],
            "publishing": [
                ("get_page", {"page_id": "p4"}),
                ("check_permission", {"user_id": "bob", "action": "publish"}),
                ("validate_links", {"page_id": "p4"}),
                ("publish_page", {"page_id": "p4"}),
            ],
        }
        self.progress = {}

    def create(self, **kwargs):
        self.calls += 1
        system = kwargs["messages"][0]["content"]
        agent = "orchestrator" if "orchestrator" in system.split("\n")[0] else "publishing"
        assert (
            "tools" in kwargs
            and any(t["function"]["name"] == "get_page" for t in kwargs["tools"])
            or agent == "orchestrator"
        )
        i = self.progress.get(agent, 0)
        steps = self.script[agent]
        usage = SimpleNamespace(prompt_tokens=1200 + 100 * i, completion_tokens=40)
        if i < len(steps):
            name, args = steps[i]
            self.progress[agent] = i + 1
            tc = SimpleNamespace(
                id=f"call{self.calls}", function=SimpleNamespace(name=name, arguments=json.dumps(args))
            )
            msg = SimpleNamespace(content=None, tool_calls=[tc])
        else:
            msg = SimpleNamespace(content="Published p4 at /content/site/blog/welcome.", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_llm_backend_drives_the_same_runtime():
    sut = load_sut(SUT_ROOT)
    case = {c.id: c for c in load_catalog()}["PUB-01"]
    client = FakeClient()
    rec = run_case(sut, case, backend="llm", llm_settings=LLMSettings(model="fake"), llm_client=client)
    assert rec["passed"], rec["failed_checks"]
    assert rec["tools"] == ["get_page", "check_permission", "validate_links", "publish_page"]
    assert rec["prompt_tokens"] > 0 and rec["agents"] == ["orchestrator", "publishing"]
    assert client.chat.completions.calls == 7  # 1 route + 1 final (orchestrator) + 4 tools + 1 final
