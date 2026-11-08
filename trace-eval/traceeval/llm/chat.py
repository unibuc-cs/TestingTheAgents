"""The agents' model behind the ``client.chat.completions.create(...)`` call that the LLM backend makes.

Two engines serve it: ``HFChatClient`` runs the model in-process with Hugging Face transformers on the local
GPU, and ``VLLMChatClient`` sends it to a vLLM server (``scripts/gpu_remote.sh`` starts one on the GPU
server). Everything else is shared, so a run gets the same prompts and the same parsing whichever engine
serves it: the prompt is built here with the model's chat template and sent as token ids, and the answer is
split into prose and tool calls here, by the tokenizer's own parser.

The default model is Gemma 4 E4B, instruction-tuned, decoded greedily at temperature 0. When
``TRACEEVAL_MODEL_LOG`` names a file, every call is appended to it as one JSON line (the last message sent,
the raw answer, tokens and time), for seeing what the model did. ``shared_client`` can put a cache of answers
in front of either engine, or replay recorded answers with no model at all (``cache.py``).
"""

import json
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from .cache import CachedClient

DEFAULT_MODEL = "google/gemma-4-E4B-it"


def to_template_messages(messages: list[dict]) -> list[dict]:
    """The backend's OpenAI-format messages in the form Gemma was trained on: tool-call arguments become
    objects, and the results of a model turn's calls go on that turn as ``tool_responses`` (name and result),
    replacing the separate ``tool`` messages. A result that is a JSON object is passed as that object; one
    that is not (the backend cuts long results to length) is passed as text."""
    out: list[dict] = []
    for m in messages:
        if m.get("role") == "tool":
            # Attach the result to the model turn that made the call, under the name of the tool it called.
            # Tool messages follow their turn directly, so that turn is the last one kept.
            turn = out[-1]
            name = next(tc["function"]["name"] for tc in turn["tool_calls"] if tc["id"] == m["tool_call_id"])
            try:
                body = json.loads(m["content"])
            except json.JSONDecodeError:
                body = m["content"]
            turn.setdefault("tool_responses", []).append({"name": name, "response": body})
            continue
        m = dict(m)
        if m.get("tool_calls"):
            # The template wants the arguments as an object. The backend keeps them as the JSON text that
            # create() wrote (or that was recorded from it), so they always decode.
            m["tool_calls"] = [
                {**tc, "function": {**tc["function"], "arguments": json.loads(tc["function"]["arguments"])}}
                for tc in m["tool_calls"]
            ]
        out.append(m)
    return out


class GemmaChat:
    """What both engines share: the prompt, the parsing of the answer and the log. An engine implements
    ``_generate``. Calls may come from several threads at once."""

    def __init__(self, model_id: str):
        from transformers import AutoTokenizer, GenerationConfig

        self.model_id = model_id
        # Only text goes in, so the tokenizer (which carries the chat template and the answer parser) is enough;
        # the full processor would also load the image and video preprocessors, which need torchvision.
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        # The tokens that end an answer (end of turn, start of a tool response), from the model's own settings.
        eos = GenerationConfig.from_pretrained(model_id).eos_token_id
        self.stop_ids = [eos] if isinstance(eos, int) else list(eos)
        self.log_path = os.environ.get("TRACEEVAL_MODEL_LOG")  # one JSON line per call when set
        self._lock = threading.Lock()  # the tokenizer and the log file are shared by the threads of a run
        # The shape the LLM backend calls: client.chat.completions.create(...)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def _generate(self, ids: list[int], temperature: float, max_tokens: int) -> tuple[str, int]:
        """The answer to the prompt ``ids``, as text with its special tokens, and its length in tokens."""
        raise NotImplementedError

    def create(self, *, messages, temperature, max_tokens, tools=None, **_ignored):
        """One model call. Of the chat-completions arguments, only ``messages``, ``tools``, ``temperature`` and
        ``max_tokens`` are used: the model is the one loaded here, and it always chooses freely between calling
        a tool and answering (the backend's ``tool_choice`` is "auto")."""
        t0 = time.perf_counter()
        with self._lock:
            ids = list(
                self.tokenizer.apply_chat_template(
                    to_template_messages(messages),
                    tools=tools,
                    tokenize=True,
                    return_dict=True,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )["input_ids"]
            )
        text, n_out = self._generate(ids, temperature, max_tokens)
        # The tokenizer's parser splits the answer into prose and tool calls. It needs the prompt, because the
        # template may have written the start of the answer. An answer it cannot parse (a malformed tool call)
        # is passed on as prose: that is the model's mistake, and the run goes on from there.
        with self._lock:
            try:
                parsed = self.tokenizer.parse_response(text, prefix=ids)
            except Exception:  # noqa: BLE001 - whatever the parser raises, the run must not crash on it
                parsed = {"content": text}
        # The call ids go back into later prompts, so they are derived from the call and not random: a run must
        # build the same prompts again for its recorded answers to be found. The prompt length keeps the ids
        # of different turns apart.
        tool_calls = [
            SimpleNamespace(
                id=f"call_{i}_{len(ids)}",
                type="function",
                function=SimpleNamespace(name=c["function"]["name"], arguments=json.dumps(c["function"]["arguments"])),
            )
            for i, c in enumerate(parsed.get("tool_calls") or [])
        ]
        usage = SimpleNamespace(prompt_tokens=len(ids), completion_tokens=n_out)
        if self.log_path:
            self._log(messages, text, usage, time.perf_counter() - t0)
        msg = SimpleNamespace(content=parsed.get("content") or None, tool_calls=tool_calls or None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)

    def _log(self, messages, text, usage, seconds):
        """Append one call to the log: which agent (the first line of its system prompt), the turn, the last
        message it was sent, the raw answer, tokens and time."""
        last = messages[-1]
        entry = {
            "agent": messages[0]["content"].split("\n", 1)[0][:80],
            "turn": len(messages),
            "last": {"role": last.get("role"), "content": str(last.get("content"))[:300]},
            "raw": text,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "seconds": round(seconds, 2),
        }
        with self._lock, open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


class HFChatClient(GemmaChat):
    """The model run in-process with transformers on the local GPU, one answer at a time."""

    def __init__(self, model_id: str):
        import torch
        from transformers import AutoModelForMultimodalLM

        super().__init__(model_id)
        self.torch = torch
        self.model = AutoModelForMultimodalLM.from_pretrained(model_id, dtype="auto", device_map="auto")
        self.model.eval()
        self._gpu = threading.Lock()  # one generation at a time, even if a run uses several threads

    def _generate(self, ids, temperature, max_tokens):
        # Greedy at temperature 0; otherwise sampling, with the model's own top-k and top-p.
        sampling = {"do_sample": True, "temperature": temperature} if temperature > 0 else {"do_sample": False}
        inputs = self.torch.tensor([ids], device=self.model.device)
        with self._gpu, self.torch.inference_mode():
            out = self.model.generate(
                input_ids=inputs, attention_mask=self.torch.ones_like(inputs), max_new_tokens=max_tokens, **sampling
            )
        new = out[0][len(ids) :]  # generate returns the prompt followed by the answer
        return self.tokenizer.decode(new, skip_special_tokens=False), int(new.shape[-1])


class VLLMChatClient(GemmaChat):
    """The model served by vLLM at ``TRACEEVAL_VLLM_URL``; by default the tunnel that
    ``scripts/gpu_remote.sh up`` opens. Many calls may run at once; the server batches them."""

    def __init__(self, model_id: str):
        from openai import OpenAI

        super().__init__(model_id)
        base_url = os.environ.get("TRACEEVAL_VLLM_URL", "http://127.0.0.1:18100/v1")
        self.client = OpenAI(base_url=base_url, api_key="EMPTY", timeout=600, max_retries=2)

    def _generate(self, ids, temperature, max_tokens):
        # The prompt goes to the plain completions endpoint as token ids, so the server sees exactly the prompt
        # built here. Special tokens and the stop token stay in the answer, as they do with the local engine,
        # so that the parser can find the tool calls.
        resp = self.client.completions.create(
            model=self.model_id,
            prompt=ids,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={
                "skip_special_tokens": False,
                "stop_token_ids": self.stop_ids,
                "include_stop_str_in_output": True,
            },
        )
        return resp.choices[0].text, int(resp.usage.completion_tokens)


_SHARED: dict[str, object] = {}  # one client per engine and process
_SHARED_LOCK = threading.Lock()
# The recorded answers the test suite replays (``--backend replay`` uses them when TRACEEVAL_CACHE is not set).
CASSETTE = Path(__file__).resolve().parents[2] / "tests" / "cassettes" / "gemma.jsonl"


def shared_client(engine: str):
    """The process-wide client of ``engine``, created on first use for the model named by ``TRACEEVAL_HF_MODEL``
    (Gemma 4 E4B by default): "hf" or "vllm" runs the model, "replay" only answers from recorded answers.

    When ``TRACEEVAL_CACHE`` names a file, the answers go through that cache (``cache.py``): a request it has
    recorded is answered from it, and any other is asked of the model and recorded. "replay" reads that file, or
    the test suite's cassette when the variable is not set."""
    with _SHARED_LOCK:  # the threads of a run may ask at the same moment; the model must load only once
        if engine not in _SHARED:
            model_id = os.environ.get("TRACEEVAL_HF_MODEL", DEFAULT_MODEL)
            cache = os.environ.get("TRACEEVAL_CACHE")
            if engine == "replay":
                client = CachedClient(None, cache or CASSETTE, model_id)
            else:
                client = {"hf": HFChatClient, "vllm": VLLMChatClient}[engine](model_id)
                if cache:
                    client = CachedClient(client, cache, model_id)
            _SHARED[engine] = client
        return _SHARED[engine]
