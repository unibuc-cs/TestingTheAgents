"""LLM agent backend over any OpenAI-compatible chat-completions endpoint with tool calling
(vLLM, OpenAI, Ollama, LiteLLM proxies, ...).

Environment variables (or explicit ``LLMSettings``):
  TRACEEVAL_LLM_BASE_URL   e.g. http://127.0.0.1:8000/v1
  TRACEEVAL_LLM_API_KEY    e.g. EMPTY for local vLLM
  TRACEEVAL_LLM_MODEL      served model name
"""

import json
import os
from dataclasses import dataclass

from ..runtime import Action


@dataclass
class LLMSettings:
    base_url: str = os.environ.get("TRACEEVAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key: str = os.environ.get("TRACEEVAL_LLM_API_KEY", "EMPTY")
    model: str = os.environ.get("TRACEEVAL_LLM_MODEL", "local-model")
    temperature: float = 0.0
    max_tokens: int = 700
    max_tool_calls_per_turn: int = 4


def build_system_prompt(agent, session, runtime) -> str:
    parts = [agent.system_prompt.strip()]
    if agent.is_orchestrator:
        lines = ["", "## Specialist agents", "Delegate exactly once with `route_to_agent`. Available agents:"]
        for name, other in runtime.agents.load_all().items():
            if other.is_orchestrator:
                continue
            lines.append(f"- `{name}`: {other.description} Triggers: {', '.join(other.triggers)}")
        parts.append("\n".join(lines))
    if agent.intents:
        parts.append("## Intents\n" + "\n".join(f"- {k}: {', '.join(v)}" for k, v in agent.intents.items()))
    for skill in session.skills:
        parts.append(f"\n---\n# SKILL: {skill.name} (v{skill.version})\n{skill.text}")
    parts.append(
        "\n## Operating rules\n- Use the tools; never claim an action you did not perform.\n"
        "- When a step of a procedure fails, stop and explain; do not improvise around guards.\n"
        "- Finish with a short confirmation message for the user."
    )
    return "\n".join(parts)


def build_user_message(session) -> str:
    slots = {k: v for k, v in session.ctx.items() if k != "request"}
    return f"Request: {session.request}\nContext: {json.dumps(slots, default=str)}"


class LLMBackend:
    def __init__(self, agent, runtime, session, settings: LLMSettings | None = None, client=None):
        self.agent = agent
        self.runtime = runtime
        self.session = session
        self.settings = settings or LLMSettings()
        if client is None:
            from openai import OpenAI  # optional dependency

            client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        self.client = client
        self.messages = [
            {"role": "system", "content": build_system_prompt(agent, session, runtime)},
            {"role": "user", "content": build_user_message(session)},
        ]
        self.tools = [runtime.dispatcher.tools[t].schema() for t in agent.tools if t in runtime.dispatcher.tools]
        self.queue: list[Action] = []

    def next_action(self, session) -> Action:
        if self.queue:
            return self.queue.pop(0)
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
        usage = getattr(resp, "usage", None)
        session.add_usage(
            getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0, runtime=self.runtime
        )
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
        if not tool_calls:
            return Action("final", message=msg.content or "")
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            self.queue.append(Action("tool", tc.function.name, args, raw=tc.id))
        return self.queue.pop(0)

    def observe(self, action: Action, result: dict):
        self.messages.append(
            {"role": "tool", "tool_call_id": action.raw, "content": json.dumps(result, default=str)[:4000]}
        )


def make_backend_factory(settings: LLMSettings | None = None, client=None):
    def factory(agent, runtime, session):
        return LLMBackend(agent, runtime, session, settings=settings, client=client)

    return factory
