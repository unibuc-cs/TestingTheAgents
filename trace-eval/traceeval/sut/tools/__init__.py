"""Tool layer: importing this package registers every tool adapter in ``registry.TOOLS``.

Business rules belong in the services, so an adapter stays thin: it receives the call from the dispatcher
together with a ``ToolContext``, hands it to the service that owns the rule, and returns that service's
result. A refusal (not found, permission denied, a failed validation) is raised as a ``ToolError``, which
the dispatcher turns into an error result for the agent."""

# Importing each adapter module runs its @tool decorators, and that is what fills the registry. The modules
# are imported only for that side effect, which is why the unused-import warning is silenced.
from . import (  # noqa: F401
    asset_tools,
    content_tools,
    control_tools,
    governance_tools,
    publish_tools,
    translation_tools,
)
from .registry import TOOLS, ToolContext, ToolSpec, get_tool  # re-exported, so callers can import them from here

__all__ = ["TOOLS", "ToolContext", "ToolSpec", "get_tool"]
