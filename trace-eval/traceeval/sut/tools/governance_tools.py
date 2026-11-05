"""Tool adapters for permissions, consent, data export and audit."""

from ..services import governance
from .registry import ToolContext, tool


@tool(
    "check_permission",
    "read",
    "Check whether a user may perform an action.",
    {
        "user_id": "user identifier",
        "action": "one of read, create, edit, attach, set_metadata, "
        "request_review, translate, publish, unpublish, schedule, "
        "approve_review, rollback, export_data",
    },
)
def check_permission(ctx: ToolContext, user_id: str, action: str):
    """Ask the governance service whether a user's roles allow an action; returns the user, the action and
    ``allowed``.

    The user is the one the agent names (the skills pass the requesting user). An unknown user is refused
    with a permission error rather than reported as not found, and an action that no role grants gives
    ``allowed`` False."""
    return governance.check_permission(ctx.state, user_id, action)


@tool(
    "check_consent",
    "read",
    "Check whether a data subject has given consent for processing.",
    {"subject_id": "data subject identifier"},
)
def check_consent(ctx: ToolContext, subject_id: str):
    """Look up a data subject's consent through the governance service: whether consent was given and for
    which purposes. A subject without a consent record is reported as not found."""
    return governance.check_consent(ctx.state, subject_id)


@tool(
    "export_user_data",
    "guarded",
    "Export all records of a data subject (requires approval token).",
    {"subject_id": "data subject identifier"},
)
def export_user_data(ctx: ToolContext, subject_id: str):
    """Export a data subject's records through the governance service; returns the record count and an
    export id.

    The service checks that the approval token belongs to the user the agent acts for and that this user
    holds the ``export_data`` permission. Consent is not checked here or in the service: the governance-ops
    skill checks it before it calls this tool. No idempotency key is passed on, so a retried call makes a
    second export."""
    return governance.export_user_data(ctx.state, subject_id, actor=ctx.user_id, approval_token=ctx.approval_token)


@tool(
    "get_audit_log",
    "read",
    "Read recent audit entries, optionally filtered by page.",
    {"page_id": "optional page identifier"},
)
def get_audit_log(ctx: ToolContext, page_id: str | None = None):
    """Read the audit log through the governance service, optionally only the entries about one page.
    ``count`` is the number of matching entries; ``entries`` holds at most the latest 20 of them."""
    return governance.get_audit_log(ctx.state, page_id)
