"""Simulated agent backend.

It follows the machine-readable procedure of the agent's entry skill step by step (resolving arguments
from the request context), routes through the keyword router, and synthesises token usage from the
size of the prompt material it "read" (agent prompt + skills + growing history). It is a stand-in for an
LLM that is reasonably obedient to its skills: mutations of skills, agent definitions, configuration and
harness code therefore change its observable behaviour in the same places an LLM's would, while runs
are free and deterministic (apart from an optional configurable flakiness rate).

The procedure step keys it understands are listed in the ``SimulatedBackend`` docstring."""

import random

from ..expressions import DotDict, resolve_value, safe_eval
from ..router import detect_intent, route
from ..runtime import Action

# Argument names that carry an identifier. When a flaky agent slips (see ``flakiness``), it garbles the first of
# these, in this order, that a tool call passes as a string.
_ID_SLOTS = ("page_id", "asset_id", "user_id", "subject_id", "job_id")


class SimulatedBackend:
    """Plays one agent for one request by working through its entry skill's procedure, with no model.

    The runtime asks ``next_action`` for the agent's next move and hands every tool result back through
    ``observe``. The procedure is the entry skill's ``## Procedure`` list in which every ``include: <skill>``
    step has already been replaced by that skill's own steps. The steps run in order, and a step may use
    these keys:

    - ``when``: a guard expression; when it is false the step is skipped.
    - ``set``: a mapping from context slots to values; the slots are written and the walk goes on.
    - ``say``: the final answer, a template whose ``{expr}`` placeholders are filled in by ``render``. It
      ends the agent's work even if steps remain.
    - ``route``: delegate the request to the specialist that the keyword router picks (the value itself is
      not read; the routing skill writes ``route: auto``).
    - ``call`` with ``args``: call the named tool with the resolved arguments.
    - ``id``: keep the result of the step's call or delegation under this name, readable as ``result.<id>``.
    - ``on_error``: what an error result does. ``stop`` (the default) ends the agent's work with "I could
      not complete the request (<error code>): <error message>", ``stop:<reason>`` puts ``<reason>`` in
      place of the error code, and ``continue`` ignores the error.
    - ``require``, ``on_fail``, ``fail_message``: a condition checked on a successful result. When it is
      false the agent stops and answers ``fail_message`` (by default "Stopped: <reason>.", the reason being
      taken from ``on_fail: stop:<reason>`` and defaulting to ``requirement_failed``), unless ``on_fail``
      is ``continue``.
    - ``then``, ``then_message``: ``then: stop`` or ``then: stop:<reason>`` makes this call the last one;
      the agent answers ``then_message`` (by default "Stopped: <reason>.", the reason defaulting to
      ``done``).

    Each step does one thing: when it has more than one of ``set``, ``say``, ``route`` and ``call``, the
    first in that order wins. Values in ``set`` and ``args`` are resolved by ``resolve_value``: ``$slot``
    copies a context slot, ``=expr`` evaluates an expression, anything else is a literal. Expressions and
    templates see the names that ``_env`` provides. When the steps run out without a ``say``, the agent
    answers "Done.".
    """

    def __init__(self, agent, runtime, session, rng: random.Random | None = None, flakiness: float = 0.0):
        self.agent = agent
        self.runtime = runtime
        self.session = session
        self.rng = rng or random.Random(0)  # drives the slip draw and the token jitter; shared by all agents of a run
        # The flattened procedure: the entry skill's steps with included skills inlined, each tagged with
        # ``_skill``, the skill it comes from. Expanding records a skill load in the trace for every skill used.
        self.steps = runtime.skills.expand(agent.entry_skill) if agent.entry_skill else []
        self.i = 0  # index of the next step to look at; the walk only ever moves forward
        self.results = DotDict()  # step id -> result of that step's call, read in expressions as result.<id>
        self.last = None  # the latest tool result, read in expressions as ``last``
        self.awaiting = None  # the step whose call is running, until observe() receives its result
        self.pending_final: str | None = None  # a closing message decided by observe(), sent at the next turn
        # Whether this agent slips once in its run, garbling one id argument. The draw is made even when the
        # flakiness is 0, so the random numbers used for the token jitter are the same whatever the setting.
        self.glitched = self.rng.random() < flakiness  # emulates an LLM slot-extraction slip
        self.glitch_used = False  # set once the slip has happened; there is at most one per agent
        # An agent that serves several kinds of request (publish, unpublish, schedule, ...) picks one by
        # matching the intent keywords against the request (the first intent listed when nothing matches),
        # unless the context already names one. Procedures read it from the context as ``intent``.
        if agent.intents and "intent" not in session.ctx:
            session.ctx["intent"] = detect_intent(session.request, agent.intents)
        # prompt material the agent "reads" on every call: system prompt + skills + request + context slots
        # (about four characters per token, a few characters of punctuation per slot, and a fixed 60 tokens
        # for the rest of the prompt). _usage adds the growing conversation on top of this base.
        context_chars = len(session.request) + sum(len(str(k)) + len(str(v)) + 6 for k, v in session.ctx.items())
        self.base_prompt = agent.prompt_tokens + sum(s.token_estimate for s in session.skills) + 60 + context_chars // 4

    # ---------------------------------------------------------------- helpers
    def _env(self):
        """The names that procedure expressions and message templates can use.

        ``ctx`` is the request context (``page_id``, ``user_id``, ... and the slots written by ``set`` steps),
        ``result`` maps step ids to their results, ``last`` is the latest tool result, ``intent`` and
        ``request`` are the detected intent and the request text, and ``config`` looks up a configuration key,
        as in ``config('publishing.require_review')`` (every lookup is recorded in the trace).
        """
        return {
            "ctx": self.session.ctx,
            "result": self.results,
            "last": self.last,
            "intent": self.session.ctx.get("intent"),
            "request": self.session.request,
            "config": self.runtime.config.get,
        }

    def _usage(self, completion: int):
        """Book the tokens of one simulated model call whose answer is ``completion`` tokens long.

        The prompt is the base prompt plus 28 tokens for every tool call made so far together with its result
        (the conversation grows as the agent works), plus 0 to 7 tokens of seeded jitter. ``add_usage`` adds
        both numbers to the session and run totals and records an ``llm.call`` trace event.
        """
        prompt = self.base_prompt + 28 * len(self.session.history) + int(self.rng.random() * 8)
        self.session.add_usage(prompt, completion, runtime=self.runtime)

    def _final(self, message: str) -> Action:
        """The final-answer action carrying ``message``, booked as a model answer of 45 tokens."""
        self._usage(45)
        return Action("final", message=message)

    # ---------------------------------------------------------------- backend protocol
    def next_action(self, session) -> Action:
        """Return the agent's next move: a tool call, a delegation (``route_to_agent``) or the final answer.

        The walk resumes where the previous call left off. Steps whose guard is false are skipped and ``set``
        steps are applied on the way, until a step needs the runtime (``call``, ``route``) or ends the agent's
        work (``say``). A stop that ``observe`` decided is answered before any further step.
        """
        # observe() decided that the agent must stop (an error, an unmet requirement or a "then: stop"): its
        # closing message is the answer now.
        if self.pending_final is not None:
            msg, self.pending_final = self.pending_final, None
            return self._final(msg)
        while self.i < len(self.steps):
            step = self.steps[self.i]
            self.i += 1
            # Rebuilt for every step, so that expressions always see the current slots and results.
            env = self._env()
            # A step whose guard does not hold is skipped, whatever it would have done.
            if "when" in step and not safe_eval(step["when"], env):
                continue
            # Writing context slots is bookkeeping rather than a model decision: no tokens are booked and the
            # walk goes straight on to the next step.
            if "set" in step:
                for k, v in step["set"].items():
                    session.ctx[k] = resolve_value(v, env)
                continue
            # The final answer ends the agent's work, even if steps remain.
            if "say" in step:
                return self._final(render(step["say"], env))
            # Delegation, used by the orchestrator: the keyword router picks the specialist whose triggers best
            # match the request, falling back to routing.default_agent. The runtime runs that agent, and its
            # answer comes back through observe() like a tool result.
            if "route" in step:
                target, info = route(
                    session.request, self.runtime.agents.load_all(), self.runtime.config.get("routing.default_agent")
                )
                self.awaiting = step
                self._usage(30)
                return Action("tool", "route_to_agent", {"agent": target, "reason": info["reason"]})
            if "call" in step:
                # A tool call, its arguments resolved from the context slots and the earlier results.
                args = resolve_value(step.get("args", {}), env)
                # A flaky agent slips once in its run: the first call that passes an id as a string gets that id
                # garbled, so the tool is asked about something that does not exist, the way an LLM sometimes
                # copies an id wrongly. A call without an id leaves the slip for a later call.
                if self.glitched and not self.glitch_used:
                    for slot in _ID_SLOTS:
                        if slot in args and isinstance(args[slot], str):
                            args[slot] = args[slot] + "-x"
                            self.glitch_used = True
                            break
                # Remember the step for observe(), and book the model call that produced this action.
                self.awaiting = step
                self._usage(35)
                return Action("tool", step["call"], args)
        # The procedure ran out without a "say": the agent closes with a generic answer.
        return self._final("Done.")

    def observe(self, action: Action, result: dict):
        """Take in the result of the call, or of the delegation, that the last step asked for.

        The result is kept as ``last`` and, when the step has an ``id``, as ``result.<id>``. Then the step's
        handlers decide whether the procedure goes on. A stop does not end the agent here: it leaves a closing
        message in ``pending_final``, which ``next_action`` returns at the next turn.
        """
        # The step that asked for this call; if none is waiting, an empty step applies all the defaults.
        step = self.awaiting or {}
        self.awaiting = None
        # As a DotDict the result can be read in expressions as last.allowed or result.fetch.path.
        self.last = DotDict(result) if isinstance(result, dict) else result
        if step.get("id"):
            self.results[step["id"]] = self.last
        env = self._env()
        # The call was refused or failed: a dispatcher gate, the tool itself, a crash, or a refused delegation.
        # "continue" carries on with the next step (this step's "then" is not looked at); anything else stops
        # with the error, under the step's own reason when it says "stop:<reason>".
        if isinstance(result, dict) and "error" in result:
            handler = step.get("on_error", "stop")
            if handler == "continue":
                return
            reason = handler.partition(":")[2] if handler.startswith("stop:") else result.get("error")
            self.pending_final = f"I could not complete the request ({reason}): {result.get('message', '')}"
            return
        # The call succeeded, but the step's condition on its result does not hold (permission not granted,
        # broken links, no consent, ...). The agent stops with fail_message, unless on_fail is "continue", in
        # which case it carries on, again without looking at "then".
        if "require" in step and not safe_eval(step["require"], env):
            handler = step.get("on_fail", "stop:requirement_failed")
            if handler == "continue":
                return
            reason = handler.partition(":")[2] or "requirement_failed"
            self.pending_final = render(step.get("fail_message", f"Stopped: {reason}."), env)
            return
        # "then: stop" ends a successful procedure after this call, for example once a review has been requested
        # instead of publishing.
        if "then" in step and str(step["then"]).startswith("stop"):
            reason = str(step["then"]).partition(":")[2] or "done"
            self.pending_final = render(step.get("then_message", f"Stopped: {reason}."), env)


def render(template: str, env: dict) -> str:
    """Render ``{expr}`` placeholders with the safe evaluator; failing expressions render as '?'.

    Text outside the placeholders is copied as it is. A placeholder ends at the first ``}``, so an expression
    cannot contain braces itself, and an unclosed ``{`` leaves the rest of the template unchanged.
    """
    out, i = [], 0
    while True:
        # Find the next placeholder; without one, or without its closing brace, the rest is plain text.
        j = template.find("{", i)
        if j < 0:
            out.append(template[i:])
            break
        k = template.find("}", j)
        if k < 0:
            out.append(template[i:])
            break
        # The text before the placeholder, then its value. An expression that fails (a missing result, a typo
        # in the skill) shows as "?", so that the message still goes out.
        out.append(template[i:j])
        try:
            out.append(str(safe_eval(template[j + 1 : k], env)))
        except Exception:
            out.append("?")
        i = k + 1
    return "".join(out)


def make_backend_factory(flakiness: float = 0.0, seed: int = 0):
    """Return the function that the runtime calls to create the backend of each agent it runs.

    All backends made by one factory share a single random generator seeded with ``seed``, so the slips and
    the token jitter of a whole run (orchestrator and specialist) can be reproduced from that seed. Make a
    fresh factory for every run, or the generator's state carries over from one run to the next.
    ``flakiness`` is the probability that an agent slips once on an id.
    """
    rng = random.Random(seed)

    def factory(agent, runtime, session):
        """Create the simulated backend that plays ``agent`` in ``session``."""
        return SimulatedBackend(agent, runtime, session, rng=rng, flakiness=flakiness)

    return factory
