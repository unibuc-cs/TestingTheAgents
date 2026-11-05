"""Tool adapters for the publishing workflow.

The checks that must pass before a page goes live (the user's permission, clean links, an approved review
when the platform requires one) are made by the publishing skill, which calls these tools in that order.
The services behind them check the links and change the page's review and publication state."""

from ..services import links, workflow
from .registry import ToolContext, tool


@tool(
    "validate_links",
    "read",
    "Validate all internal links, external URLs and asset references of a page.",
    {"page_id": "page identifier"},
)
def validate_links(ctx: ToolContext, page_id: str):
    """Check every link of a page through the link service; returns how many were checked and which are
    broken.

    Internal links must point to the path of an existing page, external URLs must be marked reachable in
    the platform's URL status table (an unlisted URL counts as broken), and asset references and attached
    assets must exist. The check itself is written to the audit log, without an actor."""
    return links.validate_links(ctx.state, page_id)


@tool("request_review", "write", "Request an editorial review for a page.", {"page_id": "page identifier"})
def request_review(ctx: ToolContext, page_id: str):
    """Ask for an editorial review of a page through the workflow service.

    The page's review becomes ``requested``, replacing whatever state it had, an approval included, and the
    request is added to the page's review history. The result gives the new review status and the number
    of review requests on record for the page. The call's idempotency key is passed through, so a retried
    call does not file a second request."""
    return workflow.request_review(ctx.state, page_id, actor=ctx.user_id, idempotency_key=ctx.idempotency_key)


@tool(
    "approve_review",
    "guarded",
    "Approve the pending review of a page (requires an approval token).",
    {"page_id": "page identifier", "reviewer_id": "user id of the approving reviewer"},
)
def approve_review(ctx: ToolContext, page_id: str, reviewer_id: str):
    """Mark a page's review as approved by ``reviewer_id``, through the workflow service.

    The service accepts the approval only when the request's approval token is that reviewer's own token
    and the reviewer holds the ``approve_review`` permission. It does not require a review to have been
    requested first, and it records the reviewer, not the user the agent acts for, as the approver. No
    idempotency key is passed on; a repeated approval changes nothing but writes another audit entry."""
    return workflow.approve_review(ctx.state, page_id, reviewer_id, approval_token=ctx.approval_token)


# Publish a page through the workflow service. The service publishes any page that exists: it sets the
# page live, clears any schedule and returns the page's status, path and published_at (a tick of the
# platform's logical clock, not a date). The acting user and the call's idempotency key are passed
# through, so a retry after a lost acknowledgement returns the first result instead of publishing again.
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
    """Schedule a page for publication through the workflow service; returns its new status and time.

    The service accepts any ``at`` of at least ten characters without parsing it, and the schedule is only
    recorded: nothing in the platform publishes the page when the time comes. No idempotency key is passed
    on; a repeated call schedules the page again and writes another audit entry."""
    # Scheduling can be switched off for the whole platform (a missing setting counts as off). The adapter
    # itself refuses the call then, before the service is reached, and the agent gets a validation error.
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
    """Take a page off the live site through the workflow service, which sets it back to ``draft``.

    The dispatcher asks for an approval token for this guarded tool (the configuration lists it among the
    tools that need one), but it only checks that the request carries a token: the token is not passed to
    the service, so its value is never compared with any user's. The unpublish permission is checked
    beforehand by the publishing skill. No idempotency key is passed on; a repeated call changes nothing
    but writes another audit entry."""
    return workflow.unpublish_page(ctx.state, page_id, actor=ctx.user_id)
