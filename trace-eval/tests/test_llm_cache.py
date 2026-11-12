"""The answer cache in front of a server that makes up tool-call ids (vLLM's chat API): with canonical ids the
recorded answers are found again whatever ids the server, or the next start of it, gives."""

from types import SimpleNamespace

from traceeval.llm.cache import CachedClient, request_key


class _Server:
    """Answers the first turn with one tool call, under an id of its own making, and the second with text."""

    def __init__(self, suffix: str):
        self.suffix = suffix
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.calls += 1
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        if request["messages"][-1]["role"] == "tool":
            msg = SimpleNamespace(content="done", tool_calls=None)
        else:
            call = SimpleNamespace(
                id=f"chatcmpl-tool-{self.suffix}", function=SimpleNamespace(name="get_page", arguments="{}")
            )
            msg = SimpleNamespace(content=None, tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


def _conversation(client):
    """Two turns, the second built from the id the first answer carries, as the llm backend does."""
    first = client.chat.completions.create(model="m", messages=[{"role": "user", "content": "hi"}], tools=[])
    call = first.choices[0].message.tool_calls[0]
    messages = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": call.id, "content": "{}"},
    ]
    second = client.chat.completions.create(model="m", messages=messages, tools=[])
    return call.id, second.choices[0].message.content


def test_canonical_ids_replay_what_a_server_with_made_up_ids_answered(tmp_path):
    path = tmp_path / "cassette.jsonl"
    server = _Server("abc")
    assert _conversation(CachedClient(server, path, "m", canonical_ids=True)) == ("chatcmpl-tool-abc", "done")
    assert server.calls == 2
    # replayed without a server: the recorded id comes back, and the second request built from it is found
    assert _conversation(CachedClient(None, path, "m", canonical_ids=True)) == ("chatcmpl-tool-abc", "done")
    # behind another start of the server the cache still answers everything
    other = _Server("zzz")
    assert _conversation(CachedClient(other, path, "m", canonical_ids=True)) == ("chatcmpl-tool-abc", "done")
    assert other.calls == 0


def test_canonical_keys_ignore_the_ids_and_exact_keys_do_not():
    def request(call_id):
        return {
            "model": "m",
            "messages": [
                {"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function"}]},
                {"role": "tool", "tool_call_id": call_id, "content": "{}"},
            ],
        }

    assert request_key(request("a"), canonical_ids=True) == request_key(request("b"), canonical_ids=True)
    assert request_key(request("a")) != request_key(request("b"))
    assert request("a")["messages"][1]["tool_call_id"] == "a"  # the request itself is left as it is
