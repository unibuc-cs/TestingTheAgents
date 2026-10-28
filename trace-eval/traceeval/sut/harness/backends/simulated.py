"""Simulated agent backend.

It follows the machine-readable procedure of the agent's entry skill step by step (resolving arguments
from the request context), routes through the keyword router, and synthesises token usage from the
size of the prompt material it "read" (agent prompt + skills + growing history). It is a stand-in for an
LLM that is reasonably obedient to its skills: mutations of skills, agent definitions, configuration and
harness code therefore change its observable behaviour in the same places an LLM's would, while runs
are free and deterministic (apart from an optional configurable flakiness rate)."""

import random

from ..expressions import DotDict, resolve_value, safe_eval
from ..router import detect_intent, route
from ..runtime import Action

_ID_SLOTS = ("page_id", "asset_id", "user_id", "subject_id", "job_id")


class SimulatedBackend:
    def __init__(self, agent, runtime, session, rng: random.Random | None = None, flakiness: float = 0.0):
        self.agent = agent
        self.runtime = runtime
        self.session = session
        self.rng = rng or random.Random(0)
        self.steps = runtime.skills.expand(agent.entry_skill) if agent.entry_skill else []
        self.i = 0
        self.results = DotDict()
        self.last = None
        self.awaiting = None
        self.pending_final: str | None = None
        self.glitched = self.rng.random() < flakiness  # emulates an LLM slot-extraction slip
        self.glitch_used = False
        if agent.intents and "intent" not in session.ctx:
            session.ctx["intent"] = detect_intent(session.request, agent.intents)
        # prompt material the agent "reads" on every call: system prompt + skills + request + context slots
        context_chars = len(session.request) + sum(len(str(k)) + len(str(v)) + 6 for k, v in session.ctx.items())
        self.base_prompt = agent.prompt_tokens + sum(s.token_estimate for s in session.skills) + 60 + context_chars // 4

    # ---------------------------------------------------------------- helpers
    def _env(self):
        return {
            "ctx": self.session.ctx,
            "result": self.results,
            "last": self.last,
            "intent": self.session.ctx.get("intent"),
            "request": self.session.request,
            "config": self.runtime.config.get,
        }

    def _usage(self, completion: int):
        prompt = self.base_prompt + 28 * len(self.session.history) + int(self.rng.random() * 8)
        self.session.add_usage(prompt, completion, runtime=self.runtime)

    def _final(self, message: str) -> Action:
        self._usage(45)
        return Action("final", message=message)

    # ---------------------------------------------------------------- backend protocol
    def next_action(self, session) -> Action:
        if self.pending_final is not None:
            msg, self.pending_final = self.pending_final, None
            return self._final(msg)
        while self.i < len(self.steps):
            step = self.steps[self.i]
            self.i += 1
            env = self._env()
            if "when" in step and not safe_eval(step["when"], env):
                continue
            if "set" in step:
                for k, v in step["set"].items():
                    session.ctx[k] = resolve_value(v, env)
                continue
            if "say" in step:
                return self._final(render(step["say"], env))
            if "route" in step:
                target, info = route(
                    session.request, self.runtime.agents.load_all(), self.runtime.config.get("routing.default_agent")
                )
                self.awaiting = step
                self._usage(30)
                return Action("tool", "route_to_agent", {"agent": target, "reason": info["reason"]})
            if "call" in step:
                args = resolve_value(step.get("args", {}), env)
                if self.glitched and not self.glitch_used:
                    for slot in _ID_SLOTS:
                        if slot in args and isinstance(args[slot], str):
                            args[slot] = args[slot] + "-x"
                            self.glitch_used = True
                            break
                self.awaiting = step
                self._usage(35)
                return Action("tool", step["call"], args)
        return self._final("Done.")

    def observe(self, action: Action, result: dict):
        step = self.awaiting or {}
        self.awaiting = None
        self.last = DotDict(result) if isinstance(result, dict) else result
        if step.get("id"):
            self.results[step["id"]] = self.last
        env = self._env()
        if isinstance(result, dict) and "error" in result:
            handler = step.get("on_error", "stop")
            if handler == "continue":
                return
            reason = handler.partition(":")[2] if handler.startswith("stop:") else result.get("error")
            self.pending_final = f"I could not complete the request ({reason}): {result.get('message', '')}"
            return
        if "require" in step and not safe_eval(step["require"], env):
            handler = step.get("on_fail", "stop:requirement_failed")
            if handler == "continue":
                return
            reason = handler.partition(":")[2] or "requirement_failed"
            self.pending_final = render(step.get("fail_message", f"Stopped: {reason}."), env)
            return
        if "then" in step and str(step["then"]).startswith("stop"):
            reason = str(step["then"]).partition(":")[2] or "done"
            self.pending_final = render(step.get("then_message", f"Stopped: {reason}."), env)


def render(template: str, env: dict) -> str:
    """Render ``{expr}`` placeholders with the safe evaluator; failing expressions render as '?'."""
    out, i = [], 0
    while True:
        j = template.find("{", i)
        if j < 0:
            out.append(template[i:])
            break
        k = template.find("}", j)
        if k < 0:
            out.append(template[i:])
            break
        out.append(template[i:j])
        try:
            out.append(str(safe_eval(template[j + 1 : k], env)))
        except Exception:
            out.append("?")
        i = k + 1
    return "".join(out)


def make_backend_factory(flakiness: float = 0.0, seed: int = 0):
    rng = random.Random(seed)

    def factory(agent, runtime, session):
        return SimulatedBackend(agent, runtime, session, rng=rng, flakiness=flakiness)

    return factory
