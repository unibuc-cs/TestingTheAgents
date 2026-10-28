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
    return governance.check_permission(ctx.state, user_id, action)


@tool(
    "check_consent",
    "read",
    "Check whether a data subject has given consent for processing.",
    {"subject_id": "data subject identifier"},
)
def check_consent(ctx: ToolContext, subject_id: str):
    return governance.check_consent(ctx.state, subject_id)


@tool(
    "export_user_data",
    "guarded",
    "Export all records of a data subject (requires approval token).",
    {"subject_id": "data subject identifier"},
)
def export_user_data(ctx: ToolContext, subject_id: str):
    return governance.export_user_data(ctx.state, subject_id, actor=ctx.user_id, approval_token=ctx.approval_token)


@tool(
    "get_audit_log",
    "read",
    "Read recent audit entries, optionally filtered by page.",
    {"page_id": "optional page identifier"},
)
def get_audit_log(ctx: ToolContext, page_id: str | None = None):
    return governance.get_audit_log(ctx.state, page_id)
