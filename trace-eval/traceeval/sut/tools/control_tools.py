"""The orchestrator's tools: delegation (handled by the runtime itself, registered so the LLM backend can see its
schema), the plan of a request that needs several specialists, and the human approval of a consequential step."""

from ..services import governance
from ..services.errors import ValidationError
from .registry import ToolContext, tool


@tool(
    "route_to_agent",
    "control",
    "Delegate work to a specialist agent: the whole request, or one step of a plan.",
    {
        "agent": "name of the specialist agent",
        "reason": "short reason for the choice",
        "task": "the specialist's own instruction for this step (default: the user's request)",
        "context": 'values the specialist needs, e.g. {"page_id": "p100"}: ids from earlier steps, an approval',
    },
)
def route_to_agent(ctx: ToolContext, agent: str, reason: str = "", task: str = "", context: dict | None = None):
    """Delegation from an orchestrator to a specialist agent.

    The runtime handles the call itself: it runs the named agent on ``task`` (or on the user's request) with the
    request context plus ``context``, and answers with that agent's name and final message
    (``delegated_response``), or with an error when no such agent exists or the chain of delegations is already
    too deep. The reason is only recorded in the trace."""
    # Never executed through the dispatcher: the runtime intercepts this tool and runs the target agent.
    return {"error": "control_tool", "message": "route_to_agent must be handled by the runtime"}


@tool(
    "make_plan",
    "read",
    "Write down the plan of a request that needs several specialists, before running its steps.",
    {"goal": "what the user wants, in one sentence", "steps": "the steps in order, each written 'agent: instruction'"},
)
def make_plan(ctx: ToolContext, goal: str, steps: list[str]):
    """Record a plan. Nothing in the platform changes: the plan goes into the trace with the call (the
    "cognition event" of a planning orchestrator), and the result repeats it with the steps numbered, for the
    orchestrator to follow. A request makes one plan, and after a step that failed for a reason another
    specialist can repair, a new one (a re-plan); ``routing.max_replans`` caps the new plans, so the limit holds
    even when the model ignores it."""
    number = ctx.state.new_plan()
    limit = int(ctx.config.get("routing.max_replans") or 0)
    if number > 1 + limit:
        raise ValidationError(f"no new plan: a request may be re-planned at most {limit} time(s)")
    return {"goal": goal, "steps": [f"{i + 1}. {s}" for i, s in enumerate(steps)]}


@tool(
    "request_approval",
    "write",
    "Ask the human approver to sign off a consequential step (publishing, scheduling, taking pages down).",
    {"summary": "what will be done, for the approver to decide on"},
)
def request_approval(ctx: ToolContext, summary: str):
    """Ask for a person's approval through the governance service. An approval comes with the approver's id and
    approval token, which the runtime adds to the request context, so the steps delegated after it carry them."""
    return governance.request_approval(ctx.state, summary, actor=ctx.user_id)
