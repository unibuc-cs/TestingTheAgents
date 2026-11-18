"""What the model is sent: tool results in Gemma's message format, and a skill's procedure as plain steps; and
which server a call goes to when a model is served on several.

The LLM backend itself, driven by a scripted client, is tested in ``test_sut.py``.
"""

import threading

from traceeval.llm.chat import Servers, to_template_messages
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.config import Config
from traceeval.sut.harness.skills import SkillLoader, render_procedure


def test_tool_results_go_on_the_model_turn():
    """Gemma reads a tool result on the model turn that made the call, with the arguments as an object."""
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
    """The model sees included skills written out, settings with their values, and none of the YAML step keys."""
    config = Config.load(SUT_ROOT / "config" / "runtime.yaml")
    text = render_procedure(SkillLoader(SUT_ROOT / "skills").expand("publishing-workflow"), config)
    assert "`check_permission`" in text and "`validate_links`" in text  # the two included skills
    assert "publishing.require_review (true)" in text
    assert not any(word in text for word in ("include:", "say:", "then:", "config(", "ctx["))


def test_each_thread_keeps_to_one_server():
    """A thread's calls all go to the server it was given first, and the next thread is given the next server: with
    as many workers as servers, each server answers one test at a time."""
    servers = Servers("http://127.0.0.1:1/v1,http://127.0.0.1:2/v1", "model")  # no call is made
    seen: dict[str, list] = {}

    def calls(name):
        seen[name] = [servers._next() for _ in range(3)]

    for name in ("a", "b"):
        thread = threading.Thread(target=calls, args=(name,))
        thread.start()
        thread.join()
    assert all(len({id(server) for server in seen[name]}) == 1 for name in seen)  # one server per thread
    assert seen["a"][0] is not seen["b"][0]  # and the two threads have different ones
