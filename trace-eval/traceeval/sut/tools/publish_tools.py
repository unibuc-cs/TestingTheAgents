"""Tool adapters for the publishing workflow."""

from ..services import links, workflow
from .registry import ToolContext, tool


@tool(
    "validate_links",
    "read",
    "Validate all internal links, external URLs and asset references of a page.",
    {"page_id": "page identifier"},
)
def validate_links(ctx: ToolContext, page_id: str):
    return links.validate_links(ctx.state, page_id)


@tool("request_review", "write", "Request an editorial review for a page.", {"page_id": "page identifier"})
def request_review(ctx: ToolContext, page_id: str):
    return workflow.request_review(ctx.state, page_id, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)


@tool(
    "approve_review",
    "guarded",
    "Approve the pending review of a page (requires an approval token).",
    {"page_id": "page identifier", "reviewer_id": "user id of the approving reviewer"},
)
def approve_review(ctx: ToolContext, page_id: str, reviewer_id: str):
    return workflow.approve_review(ctx.state, page_id, reviewer_id, approval_token=ctx.approval_token)


@tool("publish_page", "write", "Publish a page to the live site.", {"page_id": "page identifier"})
def publish_page(ctx: ToolContext, page_id: str):
    return workflow.publish_page(ctx.state, page_id, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)


@tool(
    "schedule_publish",
    "write",
    "Schedule a page to be published at a given time.",
    {"page_id": "page identifier", "at": "ISO-8601 timestamp"},
)
def schedule_publish(ctx: ToolContext, page_id: str, at: str):
    if not ctx.config.get("publishing.allow_scheduling"):
        from ..services.errors import ValidationError

        raise ValidationError("scheduling is disabled by configuration")
    return workflow.schedule_publish(ctx.state, page_id, at, actor=ctx.user_id)


@tool(
    "unpublish_page",
    "guarded",
    "Take a page off the live site (requires an approval token).",
    {"page_id": "page identifier"},
)
def unpublish_page(ctx: ToolContext, page_id: str):
    return workflow.unpublish_page(ctx.state, page_id, actor=ctx.user_id)
