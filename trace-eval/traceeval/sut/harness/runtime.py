"""The agent loop. Backend-agnostic: a backend proposes the next action (tool call or final answer);
the runtime enforces the step budgets, dispatches tools, handles delegation between agents (the whole request,
or one step of an orchestrator's plan) and records agent transitions."""

from dataclasses import dataclass, field
from pathlib import Path

from .agents import AgentLoader
from .dispatcher import Dispatcher
from .skills import SkillLoader

# How deep delegation may nest.
# The entry agent (the one the request is addressed to) runs at depth 0
# - each delegation runs its target one level deeper
# - an agent may delegate only while its own depth is below this limit.
# E.g., with the limit at 3, the orchestrator can hand the request to a specialist, that specialist can
# hand it on, and the next agent can hand it on once more; at 0, no agent may delegate at all.
MAX_DELEGATION_DEPTH = 3


@dataclass
class Action:
    """One move proposed by a backend: call a tool, or end the agent's turn with an answer."""

    type: str  # "tool" | "final"
    name: str | None = None  # the tool to call; None for a final answer
    args: dict = field(default_factory=dict)  # the arguments the backend chose for the tool
    message: str = ""  # the answer text of a final action
    raw: object = None  # backend-specific handle (e.g. tool_call_id)


@dataclass
class Session:
    """What one agent starts its turn with: its definition and skills, the request and its context. The
    backend builds the agent's prompt from it."""

    agent: object  # the AgentDef of the agent this session belongs to
    skills: list  # the Skill objects named in the agent definition, loaded when the agent started
    ctx: dict  # the request context (user id, page id, approval token, ...), shared by all agents of the run
    request: str


class Runtime:
    """Runs one request through the agents: the entry agent, and every agent it delegates to.

    A backend decides what an agent does next, and the runtime carries the decision
    out: it sends tool calls to the dispatcher, handles ``route_to_agent`` itself by running the target
    agent, and stops an agent that would go over a step budget. Each agent has a budget of its own
    (``runtime.max_tool_calls``) and the run has one in total (``runtime.max_run_tool_calls``), so that a plan
    over several agents fits while no single agent loops for long. The total, the token totals and the
    termination reason belong to the whole run, so all agents of a delegation chain share them, and a
    Runtime serves a single request.

    ``backend_factory(agent, runtime, session)`` makes a fresh backend for every agent turn. A backend
    offers ``next_action()``, which returns an ``Action``, and ``observe(action, result)``, which
    receives the result of that action.
    """

    def __init__(self, sut_dir: str | Path, config, state, tracer, backend_factory, faults, tools: dict):
        sut_dir = Path(sut_dir)  # root of the SUT copy; agent definitions and skills are read from it
        self.config = config  # runtime settings: config/runtime.yaml plus any overrides for this run
        self.state = state  # the in-memory platform data that the tools read and change
        self.tracer = tracer  # the trace recorder that every event of the run goes to
        self.backend_factory = backend_factory
        self.agents = AgentLoader(sut_dir / "agents")
        self.skills = SkillLoader(sut_dir / "skills", tracer=tracer)  # every skill load is traced
        self.dispatcher = Dispatcher(tools, config, state, tracer, faults)  # every tool call except delegation
        # State of the whole run, shared by all agents of the delegation chain.
        self.steps = 0  # tool calls and delegations made so far by all agents; the run's budget limits it
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.termination_reason = "final"  # becomes "max_tool_calls" when an agent is stopped by the budget
        self.agent_path: list[str] = []  # the agents in the order they started, the entry agent first

    def add_usage(self, agent_name: str, prompt: int, completion: int):
        """Book the tokens of one model call made by ``agent_name``: an ``llm.call`` event in the trace (the
        trace's token totals are summed from these events) and the totals of the whole run."""
        self.tracer.event("llm.call", agent=agent_name, prompt_tokens=prompt, completion_tokens=completion)
        self.prompt_tokens += prompt
        self.completion_tokens += completion

    # ---------------------------------------------------------------- public entry point
    def run(self, agent_name: str, request: str, context: dict) -> dict:
        """Run ``request`` through ``agent_name`` (and every agent it delegates to); return a summary.

        ``context`` holds the request slots (user id, page id, approval token, ...). Keys that start with
        an underscore are switches for the harness itself, such as ``_route_only``, which skips running
        the chosen specialist; they are kept out of the trace. The summary gives the final message, the
        number of steps, why the run ended, the token totals and the agents in the order they ran.
        """
        # Work on a copy, so that neither the runtime nor the agents' procedures change the caller's dict.
        # The request itself becomes a slot as well.
        ctx = dict(context)
        ctx["request"] = request
        # The trace gets the context without the harness switches.
        public_ctx = {k: v for k, v in ctx.items() if not k.startswith("_")}
        self.tracer.event("run.start", agent=agent_name, request=request, context=public_ctx)
        # Every write this request makes takes its idempotency key from the request id (see the dispatcher).
        self.dispatcher.start_request(self.state.next_request_id())
        # The entry agent runs at depth 0; any delegation runs nested inside this call.
        message = self._run_agent(agent_name, request, ctx, depth=0)
        # Close the trace with the totals of the run. The final message the trace reports is the one in
        # this event.
        self.tracer.event(
            "run.end",
            message=message,
            steps=self.steps,
            termination=self.termination_reason,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )
        return {
            "message": message,
            "steps": self.steps,
            "termination": self.termination_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "agent_path": list(self.agent_path),
        }

    # ---------------------------------------------------------------- agent loop
    def _run_agent(self, agent_name: str, request: str, ctx: dict, depth: int) -> str:
        """Run one agent's turn and return its final message. The turn ends when the backend gives a final
        answer or when the run's step budget is used up. ``depth`` is the number of delegations that led
        to this agent (0 for the entry agent)."""
        # Announce the agent. Version and digest identify exactly which definition ran.
        agent = self.agents.load(agent_name)
        self.agent_path.append(agent_name)
        self.tracer.event("agent.start", agent=agent.name, version=agent.version, digest=agent.digest, depth=depth)
        # Load the skills the definition names; each load is traced, so the run depends on these skills.
        skills = [self.skills.load(s) for s in agent.skills]
        # An orchestrator chooses by reading the triggers and the description of every specialist (the LLM
        # backend shows the model both). Record that for all of them, not just the one chosen: a change to
        # any of these fields can change the choice.
        if agent.is_orchestrator:
            for other in self.agents.load_all().values():
                if not other.is_orchestrator:
                    self.tracer.event("agent.consult", agent=other.name, fields=["triggers", "description"])
        # A fresh session and backend for this turn. A delegated agent gets a copy of the delegating agent's
        # context with the values the delegation passed (see _delegate).
        session = Session(agent=agent, skills=skills, ctx=ctx, request=request)
        backend = self.backend_factory(agent, self, session)
        # Two budgets, both counting tool calls with delegations included: this agent's own steps, and the steps
        # of the whole run.
        max_tool_calls = int(self.config.get("runtime.max_tool_calls"))
        max_run_tool_calls = int(self.config.get("runtime.max_run_tool_calls"))
        steps = 0  # this agent's own steps so far
        while True:
            # Ask the backend for the next move. A final answer ends the turn, even when the budget is spent.
            action = backend.next_action()
            if action.type == "final":
                self.tracer.event("agent.end", agent=agent.name, message=action.message)
                return action.message
            # A budget is used up: the call is not made, the agent stops with a fixed message (which the
            # agent that delegated to it receives as its answer), and the run is marked as cut short.
            if steps >= max_tool_calls or self.steps >= max_run_tool_calls:
                self.termination_reason = "max_tool_calls"
                self.tracer.event("agent.end", agent=agent.name, message="step limit reached")
                return "I stopped because the tool-call limit was reached before the task completed."
            # Count the step, then carry it out. A delegation is handled here, by running the target agent;
            # every other call goes through the dispatcher and its gates.
            steps += 1
            self.steps += 1
            if action.name == "route_to_agent":
                result = self._delegate(agent, action, request, ctx, depth)
            else:
                result = self.dispatcher.call(agent, action.name, action.args, ctx)
                # A person's approval holds for the rest of the request: the steps delegated after it carry it.
                if action.name == "request_approval" and result.get("approved"):
                    ctx.update(result.get("pass_on") or {})
            # Let the backend see the result before it plans its next move.
            backend.observe(action, result)

    def _delegate(self, agent, action: Action, request: str, ctx: dict, depth: int) -> dict:
        """Carry out a ``route_to_agent`` call. The target agent runs one level deeper, on its own instruction
        (``task``; the request itself when there is none) and on the request context plus the values the call
        passes (``context``: the ids earlier steps of a plan reported). Its final message comes back as
        the result of the call. An unknown target, a context that is not an object, or a chain that is
        already at the depth limit gets an error result instead, which the delegating agent sees like any
        other refused call."""
        target = action.args.get("agent")
        reason = action.args.get("reason", "")
        task = action.args.get("task") or request
        slots = action.args.get("context") or {}
        # Refuse a target that has no definition: a model can invent an agent name.
        if target not in self.agents.available():
            self.tracer.event("agent.route", source=agent.name, target=target, status="error", reason=reason)
            return {"error": "unknown_agent", "message": f"no agent named '{target}'"}
        if not isinstance(slots, dict):
            self.tracer.event("agent.route", source=agent.name, target=target, status="error", reason="bad_context")
            return {"error": "invalid_arguments", "message": "context must be an object of named values"}
        # Refuse to nest deeper than the limit, which also ends any chain of agents handing the request on.
        if depth >= MAX_DELEGATION_DEPTH:
            self.tracer.event("agent.route", source=agent.name, target=target, status="error", reason="max_depth")
            return {"error": "max_delegation_depth", "message": "delegation depth exceeded"}
        # The delegation is accepted and recorded as a route, with the instruction and the values passed on.
        self.tracer.event(
            "agent.route", source=agent.name, target=target, status="ok", reason=reason, task=task, context=slots
        )
        if ctx.get("_route_only"):
            # routing-dataset evaluation: score the delegation decision without executing the specialist
            return {"agent": target, "delegated_response": f"(route-only evaluation: delegated to {target})"}
        # Run the target agent on a context of its own, so that values passed to one step do not leak into the
        # next; its final answer is what the delegating agent observes.
        message = self._run_agent(target, task, {**ctx, **slots, "request": task}, depth + 1)
        return {"agent": target, "delegated_response": message}
