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


def test_tool_results_go_on_the_model_turn():
    """Gemma reads a tool result on the model turn that made the call, with the arguments as an object."""
    from traceeval.llm.chat import to_template_messages

    call = {"id": "c1", "type": "function", "function": {"name": "get_page", "arguments": '{"page_id": "p4"}'}}
    msgs = [
        {"role": "user", "content": "publish p4"},
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "c1", "content": '{"status": "draft"}'},
    ]
    out = to_template_messages(msgs)
    assert [m["role"] for m in out] == ["user", "assistant"]
    assert out[1]["tool_calls"][0]["function"]["arguments"] == {"page_id": "p4"}
    assert out[1]["tool_responses"] == [{"name": "get_page", "response": {"status": "draft"}}]


def test_procedure_reads_as_plain_steps():
    """The model sees included skills written out, settings with their values and no simulator keywords."""
    from traceeval.sut.harness.config import Config
    from traceeval.sut.harness.skills import SkillLoader, render_procedure

    config = Config.load(SUT_ROOT / "config" / "runtime.yaml")
    text = render_procedure(SkillLoader(SUT_ROOT / "skills").expand("publishing-workflow"), config)
    assert "`check_permission`" in text and "`validate_links`" in text  # the two included skills
    assert "publishing.require_review (true)" in text
    assert not any(word in text for word in ("include:", "say:", "then:", "config(", "ctx["))
