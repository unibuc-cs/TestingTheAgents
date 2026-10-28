class ToolError(Exception):
    """Base class for errors surfaced to the agent as tool results."""

    code = "tool_error"
    retryable = False

    def to_dict(self):
        return {"error": self.code, "message": str(self)}


class NotFound(ToolError):
    code = "not_found"


class PermissionDenied(ToolError):
    code = "permission_denied"


class ValidationError(ToolError):
    code = "validation_error"


class ApprovalRequired(ToolError):
    code = "approval_required"


class TransientError(ToolError):
    """A transient infrastructure failure (timeout, 503). Safe to retry *with* an idempotency key."""

    code = "transient_error"
    retryable = True
