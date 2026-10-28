"""The agent loop. Backend-agnostic: a backend proposes the next action (tool call or final answer);
the runtime enforces the step budget, dispatches tools, handles delegation between agents and records
agent transitions. The same loop drives the simulated backend and the LLM backend."""

from dataclasses import dataclass, field
from pathlib import Path

from .agents import AgentLoader
from .dispatcher import Dispatcher
from .skills import SkillLoader

MAX_DELEGATION_DEPTH = 2


@dataclass
class Action:
    type: str  # "tool" | "final"
    name: str | None = None
    args: dict = field(default_factory=dict)
    message: str = ""
    raw: object = None  # backend-specific handle (e.g. tool_call_id)


@dataclass
class Session:
    agent: object
    skills: list
    ctx: dict
    request: str
    history: list = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0

    def add_usage(self, prompt: int, completion: int, runtime=None):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.llm_calls += 1
        if runtime is not None:
            runtime.tracer.event("llm.call", agent=self.agent.name, prompt_tokens=prompt, completion_tokens=completion)
            runtime.prompt_tokens += prompt
            runtime.completion_tokens += completion


class Runtime:
    def __init__(self, sut_dir: str | Path, config, state, tracer, backend_factory, faults, tools: dict):
        self.sut_dir = Path(sut_dir)
        self.config = config
        self.state = state
        self.tracer = tracer
        self.backend_factory = backend_factory
        self.agents = AgentLoader(self.sut_dir / "agents")
        self.skills = SkillLoader(self.sut_dir / "skills", tracer=tracer)
        self.dispatcher = Dispatcher(tools, config, state, tracer, faults)
        self.steps = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.termination_reason = "final"
        self.agent_path: list[str] = []

    # ---------------------------------------------------------------- public entry point
    def run(self, agent_name: str, request: str, context: dict) -> dict:
        ctx = dict(context)
        ctx["request"] = request
        public_ctx = {k: v for k, v in ctx.items() if not k.startswith("_")}
        self.tracer.event("run.start", agent=agent_name, request=request, context=public_ctx)
        message = self._run_agent(agent_name, request, ctx, depth=0)
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
        agent = self.agents.load(agent_name)
        self.agent_path.append(agent_name)
        self.tracer.event("agent.start", agent=agent.name, version=agent.version, digest=agent.digest, depth=depth)
        skills = [self.skills.load(s) for s in agent.skills]
        if agent.is_orchestrator:
            for other in self.agents.load_all().values():
                if not other.is_orchestrator:
                    self.tracer.event("agent.consult", agent=other.name, fields=["triggers", "description"])
        session = Session(agent=agent, skills=skills, ctx=ctx, request=request)
        backend = self.backend_factory(agent, self, session)
        max_tool_calls = int(self.config.get("runtime.max_tool_calls"))
        while True:
            action = backend.next_action(session)
            if action.type == "final":
                self.tracer.event("agent.end", agent=agent.name, message=action.message)
                return action.message
            if self.steps >= max_tool_calls:
                self.termination_reason = "max_tool_calls"
                self.tracer.event("agent.end", agent=agent.name, message="step limit reached")
                return "I stopped because the tool-call limit was reached before the task completed."
            self.steps += 1
            if action.name == "route_to_agent":
                result = self._delegate(agent, action, request, ctx, depth)
            else:
                result = self.dispatcher.call(agent, action.name, action.args, ctx)
            session.history.append((action, result))
            backend.observe(action, result)

    def _delegate(self, agent, action: Action, request: str, ctx: dict, depth: int) -> dict:
        target = action.args.get("agent")
        reason = action.args.get("reason", "")
        if target not in self.agents.available():
            self.tracer.event("agent.route", source=agent.name, target=target, status="error", reason=reason)
            return {"error": "unknown_agent", "message": f"no agent named '{target}'"}
        if depth >= MAX_DELEGATION_DEPTH:
            self.tracer.event("agent.route", source=agent.name, target=target, status="error", reason="max_depth")
            return {"error": "max_delegation_depth", "message": "delegation depth exceeded"}
        self.tracer.event("agent.route", source=agent.name, target=target, status="ok", reason=reason)
        if ctx.get("_route_only"):
            # routing-dataset evaluation: score the delegation decision without executing the specialist
            return {"agent": target, "delegated_response": f"(route-only evaluation: delegated to {target})"}
        message = self._run_agent(target, request, ctx, depth + 1)
        return {"agent": target, "delegated_response": message}
