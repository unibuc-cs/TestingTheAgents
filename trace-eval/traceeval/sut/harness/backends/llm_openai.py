"""LLM agent backend over any OpenAI-compatible chat-completions endpoint with tool calling
(vLLM, OpenAI, Ollama, LiteLLM proxies, ...).

The model sees the agent's system prompt, its skills (the prose, and the procedure written as numbered steps,
with included skills written out and settings shown with their values), the routing triggers and the intents.
It then decides every step itself, and its tool calls go through the same runtime and dispatcher.

Environment variables (or explicit ``LLMSettings``); the defaults reach Qwen as ``scripts/gpu_remote.sh up qwen``
serves it:
  TRACEEVAL_LLM_BASE_URL   default http://127.0.0.1:18101/v1
  TRACEEVAL_LLM_API_KEY    default EMPTY (a local vLLM server needs none)
  TRACEEVAL_LLM_MODEL      default Qwen/Qwen3.8-27B-FP8
"""

import json
import os
from dataclasses import dataclass

from ..runtime import Action
from ..skills import render_procedure, replace_procedure

# Sent once when the model ends its work without a word, so that the user is told what happened. A step that
# stops the agent says what to answer; that answer carries the facts the user needs (which link, which job).
REPLY_NUDGE = (
    "Reply to the user now. If you stopped at a step that says what to answer, give that answer with its values "
    "filled in; otherwise say in one or two sentences what you did."
)


@dataclass
class LLMSettings:
    """Where the model is served and how it is called.

    The defaults of the endpoint, key and model come from the environment variables listed above. They are
    read once, when this module is imported, so a variable set later does not change them; pass explicit
    values instead.
    """

    base_url: str = os.environ.get("TRACEEVAL_LLM_BASE_URL", "http://127.0.0.1:18101/v1")
    api_key: str = os.environ.get("TRACEEVAL_LLM_API_KEY", "EMPTY")
    model: str = os.environ.get("TRACEEVAL_LLM_MODEL", "Qwen/Qwen3.8-27B-FP8")
    temperature: float = 0.0  # 0 keeps the model's choices as repeatable as the server allows
    max_tokens: int = 700  # the most tokens the model may write in one answer
    max_tool_calls_per_turn: int = 4  # tool calls taken from one answer; any further ones are dropped


def build_system_prompt(agent, session, runtime) -> str:
    """The system prompt of ``agent``: its own prompt, followed by everything it works from.

    The orchestrator also gets the specialists with their descriptions and routing triggers and the default
    agent, an agent with intents gets their keywords, every skill of the session follows, and a few operating
    rules close the prompt. The sections are joined with newlines.
    """
    parts = [agent.system_prompt.strip()]
    # The orchestrator has to pick the specialist itself, so it is shown each one's description and triggers,
    # and where a request goes that no specialist owns (routing.default_agent).
    if agent.is_orchestrator:
        lines = ["", "## Specialist agents", "Delegate exactly once with `route_to_agent`. Available agents:"]
        for name, other in runtime.agents.load_all().items():
            if other.is_orchestrator:
                continue
            lines.append(f"- `{name}`: {other.description} Triggers: {', '.join(other.triggers)}")
        lines.append(
            f"If no specialist owns the request, delegate it to `{runtime.config.get('routing.default_agent')}`."
        )
        parts.append("\n".join(lines))
    # The keywords of each intent; the procedure's steps depend on the intent the agent picks.
    if agent.intents:
        parts.append("## Intents\n" + "\n".join(f"- {k}: {', '.join(v)}" for k, v in agent.intents.items()))
    # Each skill under its own heading. The entry skill's procedure is written out as numbered steps (included
    # skills in place, settings with their current values); a skill it includes points there instead of
    # repeating its steps.
    for skill in session.skills:
        if skill.name == agent.entry_skill:
            steps = render_procedure(runtime.skills.expand(skill.name), runtime.config)
        else:
            steps = f"Where these steps apply, they are written out in the procedure of `{agent.entry_skill}`."
        text = replace_procedure(skill.text, steps)
        parts.append(f"\n---\n# SKILL: {skill.name} (v{skill.version})\n{text}")
    # Rules that hold for every agent, whatever its skills say.
    parts.append(
        "\n## Operating rules\n- Use the tools; never claim an action you did not perform.\n"
        "- When a step of a procedure fails, stop and explain; do not improvise around guards.\n"
        "- Finish with a short confirmation message for the user."
    )
    return "\n".join(parts)


def build_user_message(session) -> str:
    """The first user message: the request, then the request context (user, page, ...) as JSON.

    The ``request`` slot is left out of the JSON because the request already has its own line. Values that
    JSON cannot encode are written with ``str``.
    """
    slots = {k: v for k, v in session.ctx.items() if k != "request"}
    return f"Request: {session.request}\nContext: {json.dumps(slots, default=str)}"


class LLMBackend:
    """Plays one agent for one request by asking a chat model what to do at each step.

    The backend keeps the whole conversation with the model: the system prompt and the request first, then
    every answer of the model and every tool result. One answer may ask for several tool calls; they are
    handed to the runtime one at a time, and the model is asked again once all of their results are in. An
    answer without tool calls is the agent's final message.
    """

    def __init__(self, agent, runtime, session, settings: LLMSettings | None = None, client=None):
        self.agent = agent
        self.runtime = runtime
        self.settings = settings or LLMSettings()
        # A caller may pass its own client (any object with the chat.completions.create shape of the OpenAI
        # client, a stub for example); otherwise connect to the configured server.
        if client is None:
            from openai import OpenAI  # optional dependency

            client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        self.client = client
        # The conversation, sent in full on every call. The model's answers and the tool results are appended
        # as the agent works.
        self.messages = [
            {"role": "system", "content": build_system_prompt(agent, session, runtime)},
            {"role": "user", "content": build_user_message(session)},
        ]
        # Function schemas of the tools this agent may use. A tool named in the agent definition that the
        # registry does not know is left out; a tool disabled by configuration is still offered, and the
        # dispatcher refuses it when it is called.
        self.tools = [runtime.dispatcher.tools[t].schema() for t in agent.tools if t in runtime.dispatcher.tools]
        self.queue: list[Action] = []  # tool calls of the latest answer not yet handed to the runtime
        self.nudged = False  # whether the model was already asked once to reply after ending without a word

    def next_action(self) -> Action:
        """Return the agent's next move: the next tool call still queued, or a fresh answer from the model.

        The token counts that the server reports for each model call are booked with the runtime.
        """
        # Calls left over from the previous answer go out one at a time before the model is asked again.
        if self.queue:
            return self.queue.pop(0)
        # One chat-completions request carrying the whole conversation. Tools are offered only when the agent
        # has some, and the model then chooses freely between calling them and answering ("auto").
        kwargs = dict(
            model=self.settings.model,
            messages=self.messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        if self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"
        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        # Book the tokens that the server reports (0 when it reports none).
        usage = getattr(resp, "usage", None)
        self.runtime.add_usage(
            self.agent.name, getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0
        )
        # At most max_tool_calls_per_turn calls are taken from the answer, and the answer goes into the
        # conversation with only those: every tool call in the conversation must be followed by its result.
        tool_calls = list(getattr(msg, "tool_calls", None) or [])[: self.settings.max_tool_calls_per_turn]
        self.messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
            if tool_calls
            else {"role": "assistant", "content": msg.content or ""}
        )
        # No tool call: the text of the answer is the agent's final message. An empty one gets a single nudge.
        if not tool_calls:
            if not (msg.content or "").strip() and not self.nudged:
                self.nudged = True
                self.messages.append({"role": "user", "content": REPLY_NUDGE})
                return self.next_action()
            return Action("final", message=msg.content or "")
        # Every kept call becomes an action that carries the call id, so that observe() can answer the right
        # call. Arguments that are not valid JSON are passed on under "_raw": the call is then refused, and the
        # model sees that error instead of the run crashing.
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            self.queue.append(Action("tool", tc.function.name, args, raw=tc.id))
        return self.queue.pop(0)

    def observe(self, action: Action, result: dict):
        """Add a tool result to the conversation, as the answer to the call it belongs to.

        The result is sent as JSON (values that JSON cannot encode are written with ``str``) and cut to 4000
        characters, so that one large result cannot flood the prompt.
        """
        self.messages.append(
            {"role": "tool", "tool_call_id": action.raw, "content": json.dumps(result, default=str)[:4000]}
        )


def make_backend_factory(settings: LLMSettings | None = None, client=None):
    """Return the function that the runtime calls to create the backend of each agent it runs.

    Every agent of a run gets the same settings and, when one is given, the same client; each agent keeps its
    own conversation with the model.
    """

    def factory(agent, runtime, session):
        """Create the LLM backend that plays ``agent`` in ``session``."""
        return LLMBackend(agent, runtime, session, settings=settings, client=client)

    return factory
