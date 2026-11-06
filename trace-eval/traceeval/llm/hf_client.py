"""A local chat model run in-process with Hugging Face transformers, behind the
``client.chat.completions.create(...)`` call that the LLM backend makes.

The default model is Gemma 4 E4B, instruction-tuned. It is loaded once per process (``shared_client``) and
stays on the GPU, so every case and every variant of a run share it. The backend's messages are in the
OpenAI chat format; Gemma's chat template reads that format directly once tool-call arguments are objects
rather than JSON strings. The model writes tool calls in its own syntax
(``<|tool_call>call:name{key:value,...}<tool_call|>``), and ``parse_tool_calls`` turns them back into
OpenAI-style calls.

Decoding is greedy when the temperature is 0, so a run repeats exactly on the same machine and software.
When ``TRACEEVAL_MODEL_LOG`` names a file, every call is appended to it as one JSON line (the last message
sent, the raw answer, tokens and time), for inspecting what the model did.
"""

import json
import os
import re
import time
from types import SimpleNamespace

DEFAULT_MODEL = "google/gemma-4-E4B-it"

_STR = '<|"|>'  # Gemma's string delimiter inside tool calls
_CALL = re.compile(r"<\|tool_call>call:([A-Za-z0-9_\-.]+)(\{.*?\})<tool_call\|>", re.S)
_THOUGHT = re.compile(r"<\|channel>.*?<channel\|>", re.S)
_MARKERS = re.compile(r"<\|tool_response>|<tool_response\|>|<turn\|>|<\|turn>model\n?|<eos>|<pad>")


def _value(s: str, i: int):
    """Parse one value of Gemma's tool-call syntax starting at ``s[i]``; return (value, next index)."""
    if s.startswith(_STR, i):
        j = s.index(_STR, i + len(_STR))
        return s[i + len(_STR) : j], j + len(_STR)
    if s[i] == "{":
        out, i = {}, i + 1
        while s[i] != "}":
            if s.startswith(_STR, i):  # a quoted key
                key, i = _value(s, i)
            else:
                j = s.index(":", i)
                key, i = s[i:j].strip(), j
            i += 1  # the ':'
            out[key], i = _value(s, i)
            if s[i] == ",":
                i += 1
        return out, i + 1
    if s[i] == "[":
        out, i = [], i + 1
        while s[i] != "]":
            item, i = _value(s, i)
            out.append(item)
            if s[i] == ",":
                i += 1
        return out, i + 1
    j = i
    while j < len(s) and s[j] not in ",}]":
        j += 1
    raw = s[i:j].strip()
    literals = {"true": True, "false": False, "null": None}
    if raw in literals:
        return literals[raw], j
    try:
        return (float(raw) if any(c in raw for c in ".eE") else int(raw)), j
    except ValueError:
        return raw, j


def parse_tool_calls(text: str) -> list[tuple[str, dict]]:
    """The tool calls written in ``text``, in order, as (name, arguments). Arguments that cannot be parsed are
    returned as ``{"_raw": <text>}``, so the dispatcher refuses the call and the model sees why."""
    calls = []
    for name, body in _CALL.findall(text):
        try:
            args, _ = _value(body, 0)
        except (ValueError, IndexError):
            args = {"_raw": body}
        calls.append((name, args if isinstance(args, dict) else {"_raw": body}))
    return calls


def final_text(text: str) -> str:
    """The prose of an answer: ``text`` without thinking, tool calls and control tokens."""
    return _MARKERS.sub("", _CALL.sub("", _THOUGHT.sub("", text))).strip()


def to_template_messages(messages: list[dict]) -> list[dict]:
    """The backend's OpenAI-format messages in the form Gemma was trained on: tool-call arguments become
    objects, and the results of a model turn's calls go on that turn as ``tool_responses`` (name and result),
    replacing the separate ``tool`` messages. A result that is a JSON object is passed as that object; one cut
    to length is passed as text."""
    out: list[dict] = []
    for m in messages:
        if m.get("role") == "tool":
            turn = out[-1]  # the assistant turn whose call this answers
            name = next(
                (tc["function"]["name"] for tc in turn["tool_calls"] if tc.get("id") == m.get("tool_call_id")),
                "unknown",
            )
            try:
                body = json.loads(m["content"])
            except (json.JSONDecodeError, TypeError):
                body = m["content"]
            turn.setdefault("tool_responses", []).append({"name": name, "response": body})
            continue
        m = dict(m)
        if m.get("tool_calls"):
            calls = []
            for tc in m["tool_calls"]:
                raw = tc["function"]["arguments"]
                try:
                    args = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    args = {"_raw": raw}
                calls.append({**tc, "function": {"name": tc["function"]["name"], "arguments": args}})
            m["tool_calls"] = calls
        out.append(m)
    return out


class HFChatClient:
    """A transformers model behind ``chat.completions.create``. Only the arguments the LLM backend passes are
    honoured: ``messages``, ``tools``, ``temperature`` and ``max_tokens``."""

    def __init__(self, model_id: str = DEFAULT_MODEL, *, enable_thinking: bool = False):
        import torch
        from transformers import AutoModelForMultimodalLM, AutoTokenizer

        self.model_id = model_id
        self.enable_thinking = enable_thinking
        self.torch = torch
        # Only text goes in, so the tokenizer (which carries the chat template) is enough; the full processor
        # would also load the image and video preprocessors, which need torchvision.
        self.processor = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForMultimodalLM.from_pretrained(model_id, dtype="auto", device_map="auto")
        self.model.eval()
        self.log_path = os.environ.get("TRACEEVAL_MODEL_LOG")
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, *, messages, tools=None, temperature=0.0, max_tokens=700, **_ignored):
        t0 = time.perf_counter()
        inputs = self.processor.apply_chat_template(
            to_template_messages(messages),
            tools=tools or None,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
            enable_thinking=self.enable_thinking,
        ).to(self.model.device)
        n_in = inputs["input_ids"].shape[-1]
        sampling = {"do_sample": True, "temperature": temperature} if temperature > 0 else {"do_sample": False}
        with self.torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=max_tokens, **sampling)
        new = out[0][n_in:]
        text = self.processor.decode(new, skip_special_tokens=False)
        calls = parse_tool_calls(text)
        content = final_text(text)
        tool_calls = [
            SimpleNamespace(
                id=f"call_{i}_{n_in}",
                type="function",
                function=SimpleNamespace(name=name, arguments=json.dumps(args)),
            )
            for i, (name, args) in enumerate(calls)
        ]
        usage = SimpleNamespace(prompt_tokens=int(n_in), completion_tokens=int(new.shape[-1]))
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                last = messages[-1]
                entry = {
                    "agent": messages[0]["content"].split("\n", 1)[0][:80],
                    "turn": len(messages),
                    "last": {"role": last.get("role"), "content": str(last.get("content"))[:300]},
                    "raw": text,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "seconds": round(time.perf_counter() - t0, 2),
                }
                fh.write(json.dumps(entry) + "\n")
        msg = SimpleNamespace(content=content or None, tool_calls=tool_calls or None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


_SHARED: dict[str, HFChatClient] = {}


def shared_client(model_id: str | None = None) -> HFChatClient:
    """The process-wide client for ``model_id`` (by default ``TRACEEVAL_HF_MODEL`` or Gemma 4 E4B), loaded on
    first use."""
    model_id = model_id or os.environ.get("TRACEEVAL_HF_MODEL", DEFAULT_MODEL)
    if model_id not in _SHARED:
        _SHARED[model_id] = HFChatClient(model_id)
    return _SHARED[model_id]
