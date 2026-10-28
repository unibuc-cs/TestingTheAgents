"""Control tools handled by the runtime itself (registered so the LLM backend can see their schema)."""

from .registry import ToolContext, tool


@tool(
    "route_to_agent",
    "control",
    "Delegate the user's request to a specialist agent.",
    {"agent": "name of the specialist agent", "reason": "short reason for the choice"},
)
def route_to_agent(ctx: ToolContext, agent: str, reason: str = ""):
    # Never executed through the dispatcher: the runtime intercepts this tool and runs the target agent.
    return {"error": "control_tool", "message": "route_to_agent must be handled by the runtime"}
