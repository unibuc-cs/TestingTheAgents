"""The answer cache in front of a server that makes up tool-call ids (vLLM's chat API): with canonical ids the
recorded answers are found again whatever ids the server, or the next start of it, gives. And the two clients of
replay-first testing: the tee that keeps a recording's answers, and the client that replays them on a changed copy."""

import json
from types import SimpleNamespace

import pytest

from traceeval.llm.cache import CachedClient, CacheMiss, Compare, ReplayFirstClient, Tee, request_key


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


class _Scripted:
    """Answers each call with the next text of ``script``, whatever the request."""

    model_id = "m"

    def __init__(self, script):
        self.script = list(script)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        msg = SimpleNamespace(content=self.script.pop(0), tool_calls=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg)], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3)
        )


def _ask(client, *contents):
    """One request whose messages have the given contents, as (system, user, then whatever followed)."""
    roles = ["system", "user", "assistant", "tool", "assistant", "tool"]
    messages = [{"role": r, "content": c} for r, c in zip(roles, contents, strict=False)]
    return client.chat.completions.create(model="m", messages=messages).choices[0].message.content


def test_tee_keeps_the_answer_given_most_often(tmp_path):
    # the same request three times, answered "b" once and "a" twice; another request once
    tee = Tee(_Scripted(["b", "a", "a", "c"]))
    assert [_ask(tee, "sys", "q") for _ in range(3)] == ["b", "a", "a"]  # every answer passes through unchanged
    assert _ask(tee, "sys", "other") == "c"
    path = tee.write(tmp_path / "cassette.jsonl")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [(e["answer"]["content"], e["asked"], e["distinct"]) for e in lines] == [("a", 3, 2), ("c", 1, 1)]
    # among equals, the first seen is kept
    tee = Tee(_Scripted(["x", "y"]))
    _ask(tee, "sys", "q"), _ask(tee, "sys", "q")
    assert json.loads(tee.write(path).read_text(encoding="utf-8"))["answer"]["content"] == "x"


def test_compare_counts_the_requests_the_model_answers_otherwise(tmp_path):
    tee = Tee(_Scripted(["one", "two"]))
    _ask(tee, "sys", "q"), _ask(tee, "sys", "q", "one", "result")
    path = tee.write(tmp_path / "cassette.jsonl")
    # the model answers the first request as recorded, the second otherwise, and gets one the cassette lacks
    compare = Compare(_Scripted(["one", "TWO", "three"]), path)
    compare.begin()
    answers = [_ask(compare, "sys", "q"), _ask(compare, "sys", "q", "one", "result"), _ask(compare, "sys", "new")]
    assert answers == ["one", "TWO", "three"]  # every answer is the model's own: nothing comes from the cassette
    assert compare.counts() == {"requests": 3, "known": 2, "differ": 1}
    compare.begin()  # the next run starts from zero
    assert compare.counts() == {"requests": 0, "known": 0, "differ": 0}


def test_replay_first_client_counts_what_replays_and_names_the_divergence(tmp_path):
    tee = Tee(_Scripted(["one", "two"]))
    _ask(tee, "sys", "q"), _ask(tee, "sys", "q", "one", "result")
    path = tee.write(tmp_path / "cassette.jsonl")

    # every request is one the cassette holds: the test replays to the end
    client = ReplayFirstClient(path, "m")
    assert (_ask(client, "sys", "q"), _ask(client, "sys", "q", "one", "result")) == ("one", "two")
    assert (client.requests, client.tokens, client.missed, client.diverged_in) == (2, 20, 0, None)

    # a tool result the original app never saw: the divergence is there, and without a model the call fails
    client.begin()
    _ask(client, "sys", "q")
    with pytest.raises(CacheMiss):
        _ask(client, "sys", "q", "one", "another result")
    assert (client.requests, client.tokens, client.missed, client.diverged_in) == (1, 10, 1, "tool result")

    # a first request the original app never made means that what the agent is sent up front changed
    client.begin()
    with pytest.raises(CacheMiss):
        _ask(client, "a reworded system prompt", "q")
    assert (client.requests, client.diverged_in) == (0, "prompt")

    # with a model behind it, the request it lacks goes there, and nothing is added to the cassette
    client.begin()
    client.live = _Scripted(["live answer"])
    assert _ask(client, "sys", "q") == "one" and _ask(client, "sys", "q", "one", "another result") == "live answer"
    assert (client.missed, client.served_tokens) == (1, 10)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
