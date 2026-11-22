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

Three more clients serve replay-first testing (``experiment/replay_first.py``). ``Tee`` stands in front of the
model while the original app is recorded and keeps every answer, which becomes the recording's own cassette.
``ReplayFirstClient`` answers from that cassette on a changed copy of the app, counts what it could answer, and
passes the requests the original app never made on to the model, or reports them when there is none.
``Compare`` stands in front of the model while the changed copies are recorded, and counts the requests the model
answers otherwise than the cassette does.
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


class Tee:
    """In front of the model while the original app is recorded: every answer passes through unchanged and is
    kept, so that the recording gets a cassette of its own (``write``). Unlike ``CachedClient`` it never answers
    in the model's place: with several repetitions the same request reaches the model several times, and the
    answers are counted. Two answers are the same when they say the same (``_said``: the text and the tool calls),
    whatever ids the server made up for the calls. Calls may come from several threads at once."""

    def __init__(self, inner, canonical_ids: bool = False):
        self.inner = inner  # the client that answers: a model, or recorded answers when a recording is replayed
        self.model_id = inner.model_id
        self.canonical_ids = canonical_ids
        self._lock = threading.Lock()
        # request key -> what each different answer says -> [the first answer that said it, how many times], in
        # order of appearance
        self.seen: dict[str, dict[str, list]] = {}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        """One model call, answered by ``inner``; the answer is noted under the request's key."""
        resp = self.inner.chat.completions.create(**request)
        record = _to_record(resp)
        said = json.dumps(_said(record), ensure_ascii=False)
        with self._lock:
            answers = self.seen.setdefault(request_key(request, self.canonical_ids), {})
            answers.setdefault(said, [record, 0])[1] += 1
        return resp

    def write(self, path: str | Path) -> Path:
        """Write the cassette: one line per request, in ``CachedClient``'s format. When the repetitions answered a
        request in more than one way, the answer kept is the one given most often, the first seen among equals.
        The path those answers lead to was recorded too, since the run that gave an answer went on from it.
        ``asked`` and ``distinct`` say how often the request came and how many different answers it got."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for key, answers in self.seen.items():
                # the first of the most frequent: a dict keeps its order, and max returns the first of equals
                kept, _ = max(answers.values(), key=lambda answer: answer[1])
                entry = {
                    "key": key,
                    "answer": kept,
                    "asked": sum(times for _, times in answers.values()),
                    "distinct": len(answers),
                }
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path


class ReplayFirstClient(CachedClient):
    """The answers recorded on the original app (a recording's cassette), in front of a changed copy of the app.

    A request the original app also made is answered from the cassette, for no tokens. Any other request is where
    the change reaches the model: with ``live`` set it goes to that client, and without it the call raises
    ``CacheMiss``, which ends the run. Nothing is ever added to the cassette. The counters describe the test in
    progress (``begin`` resets them), so the tests must run one at a time."""

    def __init__(self, path: str | Path, model_id: str, canonical_ids: bool = False, live=None):
        super().__init__(None, path, model_id, canonical_ids)
        self.live = live  # the model asked for what the cassette lacks; None: replay only
        self.begin()

    def begin(self):
        """Before each test: forget what the one before did."""
        self.requests = 0  # requests answered from the cassette before the first one it lacks
        self.tokens = 0  # the tokens of those requests: the part of the test that needs no model
        self.missed = 0  # requests the cassette lacks; 0 means the test replays to the end
        self.served_tokens = 0  # the tokens of every request the cassette answered, also after a missed one
        self.diverged_in = None  # how the change reached the model first: "prompt" or "tool result"

    def create(self, **request):
        """One model call: from the cassette if the original app made the same request, else from ``live``."""
        answer = self.answers.get(request_key(request, self.canonical_ids))
        if answer is not None:
            used = answer["prompt_tokens"] + answer["completion_tokens"]
            self.served_tokens += used
            if not self.missed:  # still on the path the original app took
                self.requests += 1
                self.tokens += used
            return _to_response(answer)
        if not self.missed:
            # A conversation opens with the system prompt and the request. If that first request is already
            # unknown, what the agent is sent up front changed (its prompt, skills, tools or task); later on,
            # every earlier answer was replayed, so only a tool result can differ.
            self.diverged_in = "prompt" if len(request.get("messages") or []) <= 2 else "tool result"
        self.missed += 1
        if self.live is None:
            raise CacheMiss("a request the original app never made: the change reaches the model here")
        return self.live.chat.completions.create(**request)


class Compare:
    """In front of the model while a changed copy of the app is recorded: every request goes to the model, and its
    answer is compared with the one the original app got for the same request, when the recording's cassette holds
    it. Nothing is answered from the cassette. Replay-first rests on a model call being a function of its request;
    this counts, on the recording's own serving setup, how often it is not.

    The counts are per run and per thread (``begin`` before a run, ``counts`` after it, both in the thread that
    makes the run), so the runs of a suite may reach the server together:

        requests       the model calls the run made
        known          those the original app made too: the cassette has the request
        known_tokens   the tokens of those calls: what answering them from the cassette would have saved, before
                       the point where the run diverges and after it
        differ         of the known ones, those the model now answers otherwise (another text, or other tool calls)
    """

    def __init__(self, inner, path: str | Path, canonical_ids: bool = False):
        self.inner = inner  # the client that answers every request
        self.model_id = inner.model_id
        self.canonical_ids = canonical_ids
        self.answers = CachedClient(None, path, inner.model_id, canonical_ids).answers  # request key -> answer
        self._run = threading.local()  # the counts of the run this thread is making
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def begin(self):
        """Before each run, in its thread: start its counts."""
        self._run.counts = {"requests": 0, "known": 0, "known_tokens": 0, "differ": 0}

    def counts(self) -> dict:
        """After a run, in its thread: what it counted."""
        return dict(getattr(self._run, "counts", {}))

    def create(self, **request):
        """One model call, answered by ``inner`` and compared with the recorded answer to the same request."""
        resp = self.inner.chat.completions.create(**request)
        counts = getattr(self._run, "counts", None)
        if counts is not None:
            counts["requests"] += 1
            recorded = self.answers.get(request_key(request, self.canonical_ids))
            if recorded is not None:
                counts["known"] += 1
                counts["known_tokens"] += resp.usage.prompt_tokens + resp.usage.completion_tokens
                counts["differ"] += _said(recorded) != _said(_to_record(resp))
        return resp


def _said(answer: dict) -> tuple:
    """What an answer says: its text and its tool calls with their arguments. The ids of the calls and the token
    counts are left out: a server may make up other ids for the same answer."""
    return answer["content"] or "", [(c["name"], c["arguments"]) for c in answer["tool_calls"]]


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
