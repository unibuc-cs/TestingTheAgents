"""A cache of model answers, keyed by exactly what the model was sent.

Each chat-completions call is identified by a hash of its whole request: the model, the messages, the tools,
the temperature and the length limit. The first time a request is seen, the wrapped client answers it and
the answer is appended to a JSON-lines file; after that it is answered from the file. Decoding is greedy and
the app has no clock and no randomness, so a run that starts from recorded answers builds the same prompts
again and replays exactly, tool-call ids and token counts included.

Without a wrapped client the cache only replays: a request it has not recorded raises ``CacheMiss``. That is
how the test suite and ``--backend replay`` run without a model (``tests/cassettes/``). Answers that a later
version of the app no longer asks for stay in the file; to drop them, record into a new file.

A server that makes up the ids of the tool calls (vLLM's chat API, which serves Qwen and gpt-oss) puts other ids
in the next start's answers, and the app sends them back in later prompts. With ``canonical_ids`` the key
replaces every tool-call id by its order of appearance in the conversation, so the recorded answers are found
again whatever the ids; the answers keep the ids the server gave.
"""

import hashlib
import json
import threading
from pathlib import Path
from types import SimpleNamespace


class CacheMiss(RuntimeError):
    """A request that was never recorded, met while the cache can only replay."""


def request_key(request: dict, canonical_ids: bool = False) -> str:
    """The hash that identifies a request: SHA-256 of its JSON with sorted keys. With ``canonical_ids`` the
    tool-call ids in the messages are replaced by their order of appearance first (``call_0``, ``call_1``, ...)."""
    if canonical_ids:
        request = _with_canonical_ids(request)
    text = json.dumps(request, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _with_canonical_ids(request: dict) -> dict:
    """A copy of ``request`` in which every tool-call id (an assistant message's ``tool_calls[i].id`` and a tool
    message's ``tool_call_id``) is numbered by its first appearance; the original is left as it is."""
    ids: dict[str, str] = {}

    def canon(i):
        return ids.setdefault(i, f"call_{len(ids)}")

    messages = []
    for m in request.get("messages") or []:
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [{**tc, "id": canon(tc.get("id"))} for tc in m["tool_calls"]]
        if "tool_call_id" in m:
            m["tool_call_id"] = canon(m["tool_call_id"])
        messages.append(m)
    return {**request, "messages": messages}


class CachedClient:
    """A chat client with the ``client.chat.completions.create(...)`` shape that answers from the file at
    ``path`` and asks ``inner`` (a Gemma client from ``chat.py``, the ``Servers`` of the llm backend, or None to
    replay only) for what it has not seen. Calls may come from several threads at once."""

    def __init__(self, inner, path: str | Path, model_id: str, canonical_ids: bool = False):
        """Read the recorded answers at ``path`` into memory; a file that does not exist yet is an empty cache."""
        self.inner = inner  # the client asked for what is not recorded; None means replay only
        self.path = Path(path)
        self.model_id = model_id  # the model name requests carry; the LLM backend reads it from the client
        self.canonical_ids = canonical_ids  # key on the tool calls' order, not on the ids a server made up
        self._lock = threading.Lock()
        self.answers: dict[str, dict] = {}  # request key -> recorded answer
        if self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        entry = json.loads(line)
                        self.answers[entry["key"]] = entry["answer"]  # a later answer to the same request wins
        # The shape the LLM backend calls: client.chat.completions.create(...)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        """One model call: the recorded answer to ``request``, or a new one from ``inner``, recorded."""
        # The key is a hash of exactly what the model is sent, so a prompt that differs in one character misses.
        key = request_key(request, self.canonical_ids)
        answer = self.answers.get(key)
        if answer is None:
            if self.inner is None:
                raise CacheMiss(
                    f"no recorded answer for this request in {self.path}; record it with a model "
                    f"(--backend vllm or hf with TRACEEVAL_CACHE={self.path})"
                )
            # Only the bookkeeping is locked, so that the threads of a run still reach the model together.
            answer = _to_record(self.inner.chat.completions.create(**request))
            with self._lock:
                self.answers[key] = answer
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"key": key, "answer": answer}, ensure_ascii=False) + "\n")
        return _to_response(answer)


def _to_record(resp) -> dict:
    """What is kept of an answer: its text, its tool calls and the token counts."""
    msg = resp.choices[0].message
    return {
        "content": msg.content,
        "tool_calls": [
            {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in (msg.tool_calls or [])
        ],
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
    }


def _to_response(answer: dict):
    """A recorded answer in the shape of a chat-completions response."""
    calls = [
        SimpleNamespace(id=c["id"], type="function", function=SimpleNamespace(name=c["name"], arguments=c["arguments"]))
        for c in answer["tool_calls"]
    ]
    msg = SimpleNamespace(content=answer["content"], tool_calls=calls or None)
    usage = SimpleNamespace(prompt_tokens=answer["prompt_tokens"], completion_tokens=answer["completion_tokens"])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)
